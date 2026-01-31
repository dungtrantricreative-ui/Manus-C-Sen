import asyncio
import json
import traceback
import os
from typing import List, Optional, Union, Dict, Any
from pydantic import Field, model_validator, BaseModel
from loguru import logger

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

# Prompts
SYSTEM_PROMPT_TEMPLATE = (
    "You are Manus-Củ-Sen, an all-capable AI assistant, aimed at solving any task presented by the user. "
    "You have various tools at your disposal that you can call upon to efficiently complete complex requests. "
    "Whether it's programming, information retrieval, file processing, web browsing, or human interaction, you can handle it all. "
    "The initial directory is: {directory}. "
    "IMPORTANT: You MUST always answer in the same language as the user's last message. "
    "If the user speaks Vietnamese, you answer in Vietnamese. If English, answer in English."
)

NEXT_STEP_PROMPT = """
Based on user needs, proactively select the most appropriate tool or combination of tools. For complex tasks, you can break down the problem and use different tools step by step to solve it. After using each tool, clearly explain the execution results and suggest the next steps.

If you want to stop the interaction at any point, use the `terminate` tool/function call.
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
            url_info = f"\\n   URL: {browser_state.get('url', 'N/A')}\\n   Title: {browser_state.get('title', 'N/A')}"
            tabs = browser_state.get("tabs", [])
            if tabs:
                tabs_info = f"\\n   {len(tabs)} tab(s) available"
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
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    current_step: int = 0

    class Config:
        arbitrary_types_allowed = True

    def initialize(self, memory):
        self.memory = memory

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            # Check if last message is user message equal to next_step_prompt to avoid duplication?
            # OpenManus appends it every time.
            user_msg = Message.user_message(self.next_step_prompt)
            # We don't append to memory permanently usually for prompts, but OpenManus does:
            # self.messages += [user_msg]
            # But here `messages` is property of memory.
            # We should probably pass it as a temporary message to ask_tool, 
            # OR append it to memory. OpenManus appends it.
            self.memory.add_message(user_msg)

        try:
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

        logger.info(f"✨ {self.name}'s thoughts: {content}")
        if self.tool_calls:
             logger.info(f"🛠️ Selected {len(self.tool_calls)} tools: {[tc.function.name for tc in self.tool_calls]}")

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
            
            logger.info(f"🎯 Tool '{command.function.name}' result: {str(result)[:100]}...")

            # Add tool response
            tool_msg = Message.tool_message(
                content=str(result), # Ensure string
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image
            )
            self.memory.add_message(tool_msg)
            results.append(str(result))
        
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
            return await self.available_tools.execute(name=name, tool_input=args)

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
        
        if self.browser_context_helper:
             await self.browser_context_helper.cleanup_browser()


class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Củ-Sen"
    description: str = "The Supreme Agent"

    # Define tools
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonTool(),
            BrowserUseTool(),
            # TerminalTool(), # Optional, but PythonTool is safer/cleaner for logic. Terminal for filesystem.
            TerminalTool(),
            SearchTool(),
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
            tc.function.name == BrowserUseTool().name
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
