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

# Prompts
SYSTEM_PROMPT_TEMPLATE = (
    "You are Manus-Cu-Sen, an all-capable AI assistant. "
    "You solve complex tasks by combining reasoning with specialized tools. "
    "CORE MISSION: Be proactive, resourceful, and professional. Avoid bothering the user unless absolutely necessary.\n"
    "SYSTEM GUIDELINES:\n"
    "1. **Proactive Search & Browse**: Use `search_tool` for general questions. IF THE USER PROVIDES A URL OR IF SEARCH RESULTS ARE POOR, YOU MUST USE `browser_use` to access the site and find information. Never claim you cannot access a site if you have `browser_use`.\n"
    "2. **Helpful Human-Interaction**: The `ask_human` tool is for HINTS, not for repeating the user's query. "
    "If you use it, you MUST explain exactly what you tried (e.g., 'Tôi đã thử tìm ở X và Y nhưng không thấy Z, bạn có gợi ý gì không?'). Never ask a question that the user has already provided the answer to in the chat history.\n"
    "3. **Dynamic Language Policy**: You may reason in English for logic, but all user-facing output (presented thoughts, tool calls to ask_human, final answers) MUST strictly match the user's language.\n"
    "4. **Precision**: Use the `editor` tool for code bug fixes instead of rewriting files. Use `planning` for multi-step tasks.\n"
    "5. **Knowledge Management**: Use the `knowledge` tool to `search` for existing solutions first. ONLY use `save` for high-value technical insights, complex fixes, or 'hard-won' lessons from tasks that were difficult or took many steps. DO NOT save ephemeral data (prices, news, dates) or simple facts. Focus on saving the 'method' or 'logic' used to overcome an obstacle.\n"
    "6. **WORKSPACE MANDATE (WINDOWS ENVIRONMENT)**: You are running on a Windows system. You MUST save all new files, data, and scripts in the `outputs/` directory. \n"
    "   - ALWAYS prepend `outputs/` to filenames in tool calls (e.g., 'outputs/report.md').\n"
    "   - NEVER use `/tmp/`, `/home/`, or any Linux-style paths.\n"
    "   - If you ignore this, the system will automatically redirect your write to `outputs/` for safety.\n"
    "The initial directory is: {directory}."
)

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
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT_TEMPLATE.format(directory=os.getcwd())
    next_step_prompt: str = NEXT_STEP_PROMPT

    llm: LLM = Field(default_factory=LLM)
    memory: Any = Field(default=None) # Set in initialization
    state: AgentState = AgentState.IDLE

    # Available tools will be set by subclass or init
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()))
    tool_choices: ToolChoice = ToolChoice.AUTO
    
    special_tool_names: List[str] = Field(default_factory=lambda: ["terminate"])
    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = PrivateAttr(default=None)
    _console: Console = PrivateAttr(default_factory=Console)
    final_answer: Optional[str] = None

    max_steps: int = 30
    current_step: int = 0

    class Config:
        arbitrary_types_allowed = True

    def initialize(self, memory):
        self.memory = memory

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            # Check if last message is already the same prompt to avoid duplication
            if not self.memory.messages or self.memory.messages[-1].content != self.next_step_prompt:
                user_msg = Message.user_message(self.next_step_prompt)
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

        # Parse output (Adapting OpenAI response to internal ToolCall)
        self.tool_calls = []
        content = response.choices[0].message.content or ""
        raw_tool_calls = response.choices[0].message.tool_calls

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
            tool_msg = Message.tool_message(
                content=str(result),
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image
            )
            self.memory.add_message(tool_msg)
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
