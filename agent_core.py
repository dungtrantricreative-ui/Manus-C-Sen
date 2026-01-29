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

# --- Terminate Tool ---
class Terminate(BaseTool):
    name: str = "terminate"
    description: str = "Terminate the current task and provide the final answer."
    parameters: dict = {
        "type": "object",
        "properties": {
            "output": {"type": "string", "description": "The final answer or summary."}
        },
        "required": ["output"]
    }

    async def execute(self, output: str) -> str:
        return output

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
        self.current_step = 0  # Reset steps for new request
        self.state = AgentState.IDLE # Reset state to idle to allow rerun
        
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
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()))
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
        
        # If no tool calls, it means the model is giving a final answer
        if not self.tool_calls:
            self.state = AgentState.FINISHED
            return False
            
        return True

    async def act(self) -> str:
        for call in self.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            logger.info(f"Action: Using {name}")
            
            result = await self.available_tools.execute(name, args)
            self.memory.add_message(Message.tool_message(result, name, call.id))
            
            # If terminate tool is called, finish execution
            if name == "terminate":
                self.state = AgentState.FINISHED
        return "Action completed."

# --- Advanced Multi-Agent Orchestrator (RL-Inspired) ---
class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Củ-Sen-Orchestrator"
    
    # System prompt optimized for Orchestration + Self-Correction (RL)
    system_prompt: str = """Act as Manus-Competition Orchestrator. 
You use a Multi-Agent loop with Self-Correction (Reinforcement Learning principles).

PHASES:
1. PLAN: Break the user request into logical sub-tasks.
2. EXECUTE: Use tools to solve sub-tasks.
3. REFLECT: Evaluate if the result meets the 'Reward' criteria (accuracy, completeness).
4. CORRECT: If reflection shows gaps, re-plan and repeat.

STRICT FORMAT:
- THINK: Orchestration reasoning.
- ACT: Tool call.
- REFLECT: Critical assessment of the observation.
- FINISH: Use 'terminate' only after successful reflection.

Efficiency: Be direct. No filler. Optimized for Gemini 2.0 Flash."""

    async def step(self):
        """Enhanced step with Reflection (CRITIC) loop"""
        # 1. THINK & ACT (Executor Phase)
        if await self.think():
            await self.act()
            
            # 2. REFLECT (Critic Phase)
            await self.reflect()

    async def reflect(self) -> bool:
        """
        Self-Correction Phase: Model evaluates its own last action results.
        Mimics a reward signal in RL.
        """
        if self.state == AgentState.FINISHED:
            return True
            
        logger.info(f"[{self.name}] Reflection Phase (Self-Critic)...")
        
        reflection_prompt = "REFLECT: Evaluate the last tool output. Is it sufficient to answer the user? If not, what is missing? State 'CONTINUE' or 'DONE'."
        
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list() + [{"role": "user", "content": reflection_prompt}]
        
        # Use a quick call to evaluate
        response = await self.llm.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            max_tokens=100
        )
        
        analysis = response.choices[0].message.content
        logger.info(f"Reflection Analysis: {analysis}")
        
        if "DONE" in analysis.upper():
            # If the critic says it's done, we don't force a finish here, 
            # let the next think() cycle decide or prompt the model to terminate.
            self.memory.add_message(Message.system_message("Reflection: Task goal met partially or fully. Proceed to finish if complete."))
            return True
        else:
            self.memory.add_message(Message.system_message(f"Reflection Correction: {analysis}. Please refine your approach."))
            return False

    def add_tool(self, tool: BaseTool):
        self.available_tools.tool_map[tool.name] = tool
