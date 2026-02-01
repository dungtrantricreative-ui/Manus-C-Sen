import asyncio
import json
import traceback
import os
from typing import List, Optional, Union, Dict, Any
from pydantic import Field, model_validator, BaseModel, PrivateAttr
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from config import settings
from schema import Message, AgentState, ToolChoice, ToolCall, Role, Function
from base_tool import BaseTool, ToolResult, ToolCollection, ToolFailure
from llm import LLM

# Prompts (New V2 with CoT)
from prompts import (
    get_system_prompt, get_reasoning_prompt, get_reflection_prompt,
    is_complex_task, NEXT_STEP_PROMPT_DETAILED, COT_REASONING_PROMPT
)

# Tools
from tools.browser_use_tool import BrowserUseTool
from tools.python_tool import PythonTool
from tools.terminate import Terminate
from tools.terminal import TerminalTool
from tools.search import SearchTool
from tools.editor import EditorTool
from tools.planning import PlanningTool
from tools.ask_human import AskHumanTool
from tools.knowledge import KnowledgeTool

# Prompts - Now imported from prompts.py for better organization
# Legacy fallback (will use new prompts module)
NEXT_STEP_PROMPT = """
Analyze the previous results. Decide if you need more info or can proceed to the next step.
If the task is finished, use `terminate`.
"""

class BrowserContextHelper:
    def __init__(self, agent):
        self.agent = agent
        self._current_base64_image: Optional[str] = None

    async def get_browser_state(self) -> Optional[dict]:
        browser_tool = self.agent.available_tools.get_tool(BrowserUseTool().name)
        if not browser_tool or not hasattr(browser_tool, "get_current_state"):
            return None
        try:
            result = await browser_tool.get_current_state()
            if result.error:
                return None
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image
            else:
                self._current_base64_image = None
            return json.loads(result.output)
        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def format_next_step_prompt(self) -> str:
        """Gets browser state and formats the browser prompt."""
        browser_state = await self.get_browser_state()
        url_info, tabs_info, content_above_info, content_below_info = "", "", "", ""
        results_info = ""

        if browser_state and not browser_state.get("error"):
            url = browser_state.get('url', 'N/A')
            title = browser_state.get('title', 'N/A')
            url_info = f"\n   URL: {url}\n   Title: {title}"
            tabs = browser_state.get("tabs", [])
            if tabs:
                tabs_info = f"\n   {len(tabs)} tab(s) available"
            # Browser-use often provides extra pixels info
            
            if self._current_base64_image:
                image_message = Message.user_message(
                    content="Current browser screenshot:",
                    base64_image=self._current_base64_image,
                )
                self.agent.memory.add_message(image_message)
                self._current_base64_image = None  # Consume the image after adding

        # Append browser info to the standard prompt
        if url_info:
             browser_context = f"\nBrowser State:\n{url_info}\n{tabs_info}"
             return NEXT_STEP_PROMPT + browser_context
        
        return NEXT_STEP_PROMPT

    async def cleanup_browser(self):
        browser_tool = self.agent.available_tools.get_tool(BrowserUseTool().name)
        if browser_tool and hasattr(browser_tool, "cleanup"):
            await browser_tool.cleanup()



class ToolCallAgent(BaseModel):
    """Base agent class for handling tool/function calls with enhanced reasoning"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = Field(default_factory=lambda: get_system_prompt(settings.MAX_STEPS))
    next_step_prompt: str = NEXT_STEP_PROMPT

    llm: LLM = Field(default_factory=LLM)
    memory: Any = Field(default=None)  # Set in initialization
    state: AgentState = AgentState.IDLE

    # Available tools will be set by subclass or init
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()))
    tool_choices: ToolChoice = ToolChoice.AUTO
    
    special_tool_names: List[str] = Field(default_factory=lambda: ["terminate"])
    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = PrivateAttr(default=None)
    _console: Console = PrivateAttr(default_factory=Console)
    _is_complex_task: bool = PrivateAttr(default=False)  # Adaptive reasoning flag
    _last_tool_result: str = PrivateAttr(default="")  # For reflection
    final_answer: Optional[str] = None

    max_steps: int = 30
    current_step: int = 0

    class Config:
        arbitrary_types_allowed = True

    def initialize(self, memory, user_input: str = ""):
        self.memory = memory
        # Detect task complexity for adaptive reasoning
        if user_input:
            self._is_complex_task = is_complex_task(user_input)

    async def think(self) -> bool:
        """Process current state and decide next actions with adaptive reasoning"""
        # Use adaptive prompt based on task complexity
        reasoning_prompt = get_reasoning_prompt(self._is_complex_task)
        effective_prompt = reasoning_prompt if self._is_complex_task else self.next_step_prompt
        
        # Add reflection on last result if available (for complex tasks)
        if self._is_complex_task and self._last_tool_result:
            reflection = get_reflection_prompt(True, self._last_tool_result)
            effective_prompt = reflection + "\n\n" + effective_prompt
            self._last_tool_result = ""  # Reset after use
        
        if effective_prompt:
            # Check if last message is already the same prompt to avoid duplication
            if not self.memory.messages or self.memory.messages[-1].content != effective_prompt:
                user_msg = Message.user_message(effective_prompt)
                self.memory.add_message(user_msg)

        try:
            # Trigger memory summarization if needed
            await self.memory.summarize(self.llm)
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.memory.messages,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            self.memory.add_message(Message.assistant_message(f"Error: {str(e)}"))
            return False

        if not response.choices:
            logger.error("LLM returned no choices.")
            self.memory.add_message(Message.assistant_message("Error: LLM returned an empty response."))
            return False

        # Parse output (Adapting OpenAI response to internal ToolCall)
        self.tool_calls = []
        content = response.choices[0].message.content or ""
        raw_tool_calls = response.choices[0].message.tool_calls

        if not content and not raw_tool_calls:
            logger.warning("LLM returned empty content and no tool calls. Retrying with a hint.")
            content = "Dường như tôi đang gặp chút vấn đề trong việc xử lý yêu cầu. Bạn có thể nói rõ hơn hoặc thử lại không?"

        if raw_tool_calls:
            for tc in raw_tool_calls:
                self.tool_calls.append(ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function=Function(
                        name=tc.function.name,
                        arguments=tc.function.arguments
                    )
                ))

        # UI: Print thoughts in a subtle box
        if content:
             self._console.print(Panel(
                 Text(content, style="italic"),
                 title="[bold cyan]Suy nghi cua Manus[/bold cyan]",
                 border_style="cyan",
                 padding=(0, 2)
             ))

        if self.tool_calls:
             tool_names = [tc.function.name for tc in self.tool_calls]
             self._console.print(f"  [bold yellow]Su dung:[/bold yellow] [cyan]{', '.join(tool_names)}[/cyan]")

        # Add assistant message to memory
        if self.tool_calls:
             assistant_msg = Message.assistant_message(content=content)
             assistant_msg.tool_calls = self.tool_calls # Manually attach
             # Or use helper if avail:
             assistant_msg = Message.from_tool_calls(tool_calls=raw_tool_calls, content=content)
             self.memory.add_message(assistant_msg)
             return True
        elif content:
             self.memory.add_message(Message.assistant_message(content))
             # If just content, maybe we are done or need more info?
             # OpenManus returns False if no tool calls in AUTO mode unless required.
             return False # Stop thinking, let user respond? 
             # Wait, if Agent is autonomous, it should keep going? 
             # OpenManus `run` loop checks this bool. If True, it calls `act`. If False, it stops `step` but `run` loop might continue if not finished?
             # OpenManus logic: if think returns True, call act. 
        
        return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            return "No tool calls to execute."

        results = []
        for command in self.tool_calls:
            self._current_base64_image = None
            
            # Execute
            result = await self.execute_tool(command)
            
            # Subtly show tool completion
            if command.function.name != "terminate":
                 self._console.print(f"  [green]Done:[/green] [dim]Cong cu '{command.function.name}' hoan tat.[/dim]")

            # Add tool response
            result_str = str(result)
            tool_msg = Message.tool_message(
                content=result_str,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image
            )
            self.memory.add_message(tool_msg)
            
            # Store result for reflection in next think cycle
            self._last_tool_result = result_str[:500]  # Limit for efficiency
            results.append(f"Tool {command.function.name} executed.")
        
        return "\\n\\n".join(results)

    async def execute_tool(self, command: ToolCall) -> Any:
        name = command.function.name
        try:
            args = json.loads(command.function.arguments)
        except:
            return f"Error: Invalid JSON arguments for {name}"

        # Special handling for Terminate
        if name.lower() == "terminate":
            # --- ANTI-LAZINESS CHECK ---
            # If we used browser_use recently, ensure we actually interact/read, not just search & quit.
            has_browser_use = False
            has_interaction = False
            
            # Check recent history (last 10 messages) for browser usage
            recent_msgs = self.memory.messages[-10:] if len(self.memory.messages) > 10 else self.memory.messages
            for msg in recent_msgs:
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.function.name == "browser_use":
                            has_browser_use = True
                            args = json.loads(tc.function.arguments)
                            action = args.get("action", "")
                            # Actions that count as "real work"
                            if action in ["click_element", "read_page", "extract_content", "input_text", "scroll_down"]:
                                has_interaction = True
            
            if has_browser_use and not has_interaction and self.current_step < self.max_steps:
                 return (
                     "⚠️ **SYSTEM INTERVENTION (ANTI-LAZINESS)**: \n"
                     "You used the browser but ONLY searched/visited. You did NOT click results or read content.\n"
                     "❌ You cannot terminate yet.\n"
                     "👉 **REQUIRED**: You MUST use `click_element` to open a result, OR `read_page`/`extract_content` to read details.\n"
                     "Do not guess the answer from search snippets."
                 )
            # ---------------------------

            self.state = AgentState.FINISHED
            res = await self.available_tools.execute(name=name, tool_input=args)
            if isinstance(res, ToolResult):
                 self.final_answer = res.output
            else:
                 self.final_answer = str(res)
            return res

        result = await self.available_tools.execute(name=name, tool_input=args)
        
        # Check for base64 image in result (ToolResult)
        if isinstance(result, ToolResult):
            if result.base64_image:
                self._current_base64_image = result.base64_image
            return result.output if result.output else result.error
        
        return result

    async def step(self) -> str:
        """Execute a single step"""
        decision = await self.think()
        if decision:
             return await self.act()
        return "Thinking complete (No tool calls)."

    async def run(self):
        """Main loop"""
        self.state = AgentState.RUNNING
        while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
            self.current_step += 1
            logger.info(f"Step {self.current_step}/{self.max_steps}")
            await self.step()
        
        # Auto-evaluate if this task is worth saving to Knowledge Base
        if self.state == AgentState.FINISHED:
            await self.evaluate_knowledge_saving()

    async def evaluate_knowledge_saving(self):
        """Hidden step to check if the finished task should be archived"""
        eval_prompt = (
            "Review your recent actions. If the task was complex, required multiple technical steps, "
            "or resulted in a 'hard-won' solution, use the `knowledge` tool to `save` the core method/logic. "
            "If it was trivial, ephemeral (news/prices), or simple, DO NOT save. "
            "Decide now (use `knowledge` or just provide a final thought)."
        )
        # Add a temporary system message for evaluation
        self.memory.add_message(Message.system_message(content=eval_prompt))
        
        # One last think/act cycle specifically for knowledge
        self.tool_choices = ToolChoice.AUTO # Ensure tools can be called
        await self.think()
        if self.tool_calls and any(tc.function.name == "knowledge" for tc in self.tool_calls):
             await self.act()


class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Cu-Sen"
    description: str = "The Supreme Agent"

    # Define tools
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonTool(),
            BrowserUseTool(),
            TerminalTool(),
            SearchTool(),
            EditorTool(),
            PlanningTool(),
            AskHumanTool(),
            KnowledgeTool(),
            Terminate()
        )
    )

    browser_context_helper: Optional[BrowserContextHelper] = None

    @model_validator(mode="after")
    def initialize_helper(self) -> "ManusCompetition":
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        original_prompt = self.next_step_prompt
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == "browser_use"
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt
        return result
