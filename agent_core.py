import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from loguru import logger

from config import settings
from schema import Role, Message, Memory, AgentState, ToolChoice, ToolCall

# --- Base Tool Logic ---
class ToolResult(BaseModel):
    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)

    def __str__(self):
        return f"Error: {self.error}" if self.error else str(self.output)

class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    def to_param(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

class ToolCollection:
    def __init__(self, *tools: BaseTool):
        self.tool_map = {tool.name: tool for tool in tools}

    def to_params(self) -> List[Dict]:
        return [tool.to_param() for tool in self.tool_map.values()]

    async def execute(self, name: str, tool_input: Dict) -> str:
        tool = self.tool_map.get(name)
        if not tool:
            return f"Error: Tool {name} not found"
        try:
            result = await tool.execute(**tool_input)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

# --- Minimal LLM Client ---
class LLM:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.BASE_URL
        )

    async def ask_tool(self, messages: List[dict], tools: List[dict]) -> Any:
        response = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        return response.choices[0].message

# --- Robust Agent Logic (Ported from OpenManus) ---
class BaseAgent(BaseModel, ABC):
    name: str
    system_prompt: str
    llm: LLM = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE
    max_steps: int = settings.MAX_STEPS
    current_step: int = 0

    class Config:
        arbitrary_types_allowed = True

    async def run(self, request: Optional[str] = None) -> str:
        if request:
            self.memory.add_message(Message.user_message(request))
        
        self.state = AgentState.RUNNING
        try:
            while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
                self.current_step += 1
                logger.info(f"[{self.name}] Step {self.current_step}/{self.max_steps}")
                await self.step()
                
                if self.is_stuck():
                    logger.warning(f"[{self.name}] Agent seems stuck, adjusting strategy...")
                    self.memory.add_message(Message.system_message("You are repeating yourself. Try a different approach."))

            return self.memory.messages[-1].content or "Finished."
        finally:
            self.state = AgentState.FINISHED

    def is_stuck(self) -> bool:
        if len(self.memory.messages) < 4: return False
        last_msgs = [m.content for m in self.memory.messages[-4:] if m.role == Role.ASSISTANT and m.content]
        return len(last_msgs) >= 2 and len(set(last_msgs)) == 1

    @abstractmethod
    async def step(self):
        pass

class ReActAgent(BaseAgent):
    @abstractmethod
    async def think(self) -> bool: pass

    @abstractmethod
    async def act(self) -> str: pass

    async def step(self):
        if await self.think():
            await self.act()

class ToolCallAgent(ReActAgent):
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection())
    tool_calls: List[ToolCall] = Field(default_factory=list)

    async def think(self) -> bool:
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list()
        response = await self.llm.ask_tool(messages, self.available_tools.to_params())
        
        self.tool_calls = response.tool_calls if response.tool_calls else []
        content = response.content or ""
        
        if content:
            logger.info(f"Thought: {content}")
        
        assistant_msg = Message.from_tool_calls(self.tool_calls, content=content) if self.tool_calls else Message.assistant_message(content)
        self.memory.add_message(assistant_msg)
        
        return bool(self.tool_calls)

    async def act(self) -> str:
        for call in self.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            logger.info(f"Action: Using {name}")
            
            result = await self.available_tools.execute(name, args)
            self.memory.add_message(Message.tool_message(result, name, call.id))
        return "Action completed."

# --- Optimization for Gemini 2.x Flash ---
class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Competition"
    system_prompt: str = """Act as Manus-Competition. Optimized for Gemini 2.0 Flash.
REASONING: Direct & logical. 
STRICT FORMAT: 
1. THINK: Logic step.
2. ACT: Call tool.
3. FINISH: Only when goal met.
No conversational filler. Max efficiency."""

    def add_tool(self, tool: BaseTool):
        self.available_tools.tool_map[tool.name] = tool
