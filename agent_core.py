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
from schema import Message, AgentState, ToolChoice, ToolCall, Role, Function, Memory
from base_tool import BaseTool, ToolResult, ToolCollection, ToolFailure
from llm import LLM

# Prompts (New V2 with CoT)
from prompts import (
    get_system_prompt, get_reasoning_prompt, get_reflection_prompt,
    is_complex_task, NEXT_STEP_PROMPT_DETAILED, COT_REASONING_PROMPT
)

# Tools
from tools import load_tools
from tools.terminate import Terminate  # Keep for core logic check

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
        browser_tool = self.agent.available_tools.get_tool("browser_use")
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
        browser_tool = self.agent.available_tools.get_tool("browser_use")
        if browser_tool and hasattr(browser_tool, "cleanup"):
            await browser_tool.cleanup()



class ToolCallAgent(BaseModel):
    """Base agent class for handling tool/function calls with structured memory and state management."""

    name: str = "toolcall"
    description: str = "An agent that can execute tool calls with high precision."

    system_prompt: str = Field(default_factory=lambda: get_system_prompt(settings.MAX_STEPS))
    next_step_prompt: str = NEXT_STEP_PROMPT

    llm: LLM = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()))
    tool_choices: ToolChoice = ToolChoice.AUTO
    
    special_tool_names: List[str] = Field(default_factory=lambda: ["terminate"])
    _console: Console = PrivateAttr(default_factory=Console)
    _is_complex_task: bool = PrivateAttr(default=False)
    _last_tool_result: str = PrivateAttr(default="")
    final_answer: Optional[str] = None

    max_steps: int = 30
    current_step: int = 0

    class Config:
        arbitrary_types_allowed = True

    def initialize(self, user_input: str = ""):
        if user_input:
            self.memory.add_message(Message.user_message(user_input))
            self._is_complex_task = is_complex_task(user_input)

    async def think(self) -> bool:
        """Process state and decide next action. Returns True if acting is needed."""
        reasoning_prompt = get_reasoning_prompt(self._is_complex_task)
        effective_prompt = reasoning_prompt if self._is_complex_task else self.next_step_prompt
        
        # Add reflection if needed
        if self._is_complex_task and self._last_tool_result:
            reflection = get_reflection_prompt(True, self._last_tool_result)
            effective_prompt = reflection + "\n\n" + effective_prompt
            self._last_tool_result = ""

        if effective_prompt:
             # TRIGGER PHASE 12: Context Pruning
             await self.memory.summarize(self.llm)
             
             self.memory.add_message(Message.user_message(effective_prompt))

        try:
            response = await self.llm.ask_tool(
                messages=self.memory.to_dict_list(),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except Exception as e:
            logger.success(f"❌ [bold red]LLM failure:[/bold red] {str(e)[:100]}")
            return False

        if not response.choices:
            return False

        assistant_msg_raw = response.choices[0].message
        content = assistant_msg_raw.content or ""
        
        # Parse tool calls using the new schema
        tool_calls = []
        if assistant_msg_raw.tool_calls:
            for tc in assistant_msg_raw.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function=Function(name=tc.function.name, arguments=tc.function.arguments)
                ))

        # Add assistant message to memory
        assistant_msg = Message.assistant_message(content=content, tool_calls=tool_calls if tool_calls else None)
        self.memory.add_message(assistant_msg)

        # UI: Thought Visualization
        if content:
             self._console.print(Panel(Text(content, style="italic"), title="🧠 Thinking", border_style="cyan"))

        if tool_calls:
             tool_names = [tc.function.name for tc in tool_calls]
             self._console.print(f"  [bold yellow]Action:[/bold yellow] [cyan]{', '.join(tool_names)}[/cyan]")
             return True
        
        return False

    async def act(self) -> str:
        """Execute tool calls from the last assistant message."""
        last_msg = self.memory.messages[-1]
        if not last_msg.tool_calls:
            return "No actions to take."

        results = []
        for tc in last_msg.tool_calls:
            result = await self.execute_tool(tc)
            
            # PHASE 12: Show results in UI
            output_str = str(result.output if hasattr(result, "output") else result)
            # Filter out empty or technical messages for cleaner UI
            if output_str and len(output_str) > 2:
                snippet = output_str[:150].replace("\n", " ") + ("..." if len(output_str) > 150 else "")
                self._console.print(f"  ✅ [bold green]{tc.function.name}:[/bold green] [white]{snippet}[/white]")
            else:
                self._console.print(f"  ✅ [green]{tc.function.name} finished (no output).[/green]")

            # Add tool result to memory
            tool_msg = Message.tool_message(
                content=output_str,
                name=tc.function.name,
                tool_call_id=tc.id
            )
            # Inherit image if result has it
            if isinstance(result, ToolResult) and result.base64_image:
                 tool_msg.base64_image = result.base64_image
            
            self.memory.add_message(tool_msg)
            results.append(f"Tool {tc.function.name} results added.")
        
        return "\n".join(results)

    async def execute_tool(self, tool_call: ToolCall) -> Any:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except:
            return f"Error: Invalid arguments for {name}"

        # Terminate check (preserved from original logic)
        if name.lower() == "terminate":
            self.state = AgentState.FINISHED
            res = await self.available_tools.execute(name=name, tool_input=args)
            self.final_answer = res.output if isinstance(res, ToolResult) else str(res)
            return res

        return await self.available_tools.execute(name=name, tool_input=args)

    async def step(self):
        if await self.think():
            await self.act()

    async def run(self):
        self.state = AgentState.RUNNING
        while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
            self.current_step += 1
            await self.step()

class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Cu-Sen"
    
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(*load_tools(settings.tools.enabled if hasattr(settings, "tools") else None))
    )

    @model_validator(mode="after")
    def inject_expert_instructions(self) -> "ManusCompetition":
        instructions = []
        for tool in self.available_tools:
            if hasattr(tool, "instructions") and tool.instructions:
                instructions.append(f"### Expert: {tool.name}\n{tool.instructions}")
        
        self.system_prompt = get_system_prompt(
            max_steps=self.max_steps,
            tool_instructions="\n\n".join(instructions)
        )
        # Initialize memory with system prompt
        self.memory.add_message(Message.system_message(self.system_prompt))
        return self
