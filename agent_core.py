import json
import asyncio
import time
import sys
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from schema import Role, Message, Memory, AgentState, ToolChoice, ToolCall
from tools.monitoring import Monitoring

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
        
        # Smart Retry Logic for Tools
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                result = await tool.execute(**tool_input)
                return str(result)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Tool {name} failed (attempt {attempt+1}). Retrying...")
                    await asyncio.sleep(1) # Small backoff
                    continue
                logger.error(f"Error executing {name} after {max_retries} retries: {str(e)}")
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

# --- LLM Client with Streaming & Retries ---
class LLM:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.BASE_URL
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def ask_tool_stream(self, messages: List[dict], tools: List[dict]) -> AsyncGenerator[Dict[str, Any], None]:
        response = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True
        )
        async for chunk in response:
            yield chunk

    async def quick_ask(self, messages: List[dict], max_tokens: int = 200) -> str:
        """For non-tool, quick reflection calls"""
        response = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            stream=False
        )
        return response.choices[0].message.content or ""

# --- Optimized Agent Core (The Manus-Củ-Sen Engine) ---
class BaseAgent(BaseModel, ABC):
    name: str
    system_prompt: str
    llm: LLM = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE
    max_steps: int = settings.MAX_STEPS
    current_step: int = 0
    
    # Intelligent Caching
    tool_cache: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    async def run(self, request: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        self.current_step = 0
        self.state = AgentState.RUNNING
        
        if request:
            self.memory.add_message(Message.user_message(request))
        
        try:
            while self.current_step < self.max_steps and self.state != AgentState.FINISHED:
                self.current_step += 1
                logger.info(f"[{self.name}] Step {self.current_step}/{self.max_steps}")
                
                async for chunk in self.step_stream():
                    yield chunk
                
                if self.state != AgentState.FINISHED:
                    # After each tool execution, perform a internal CRITIC verification
                    async for crit in self.reflect_stream():
                        yield crit

                if self.is_stuck():
                    logger.warning(f"[{self.name}] Agent stuck. Forcing rethink.")
                    self.memory.add_message(Message.system_message("Reflection: You are repeating yourself. Try a different approach or tool."))

        finally:
            self.state = AgentState.FINISHED

    def is_stuck(self) -> bool:
        if len(self.memory.messages) < 4: return False
        last_msgs = [m.content for m in self.memory.messages[-4:] if m.role == Role.ASSISTANT and m.content]
        return len(last_msgs) >= 2 and len(set(last_msgs)) == 1

    @abstractmethod
    async def step_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        pass

    @abstractmethod
    async def reflect_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        pass

class ToolCallAgent(BaseAgent):
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()))
    tool_calls: List[ToolCall] = Field(default_factory=list)

    async def step_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        # 1. ORCHESTRATOR / PLANNER Phase
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list()
        
        full_content = ""
        tool_calls_data = []
        
        yield {"type": "status", "content": "🔧 Using tool: thinking (Manager)"}
        
        async for chunk in self.llm.ask_tool_stream(messages, self.available_tools.to_params()):
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                yield {"type": "content", "content": delta.content}
            
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    if len(tool_calls_data) <= tc_delta.index:
                        tool_calls_data.append({
                            "id": tc_delta.id,
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })
                    
                    if tc_delta.id:
                        tool_calls_data[tc_delta.index]["id"] = tc_delta.id
                    if tc_delta.function.name:
                        tool_calls_data[tc_delta.index]["function"]["name"] = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls_data[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

        self.tool_calls = [ToolCall(**tc) for tc in tool_calls_data]
        
        assistant_msg = Message.from_tool_calls(self.tool_calls, content=full_content) if self.tool_calls else Message.assistant_message(full_content)
        self.memory.add_message(assistant_msg)
        
        if not self.tool_calls:
            self.state = AgentState.FINISHED
            return

        # 2. EXECUTOR Phase
        for call in self.tool_calls:
            name = call.function.name
            args_str = call.function.arguments
            args = json.loads(args_str)
            
            yield {"type": "status", "content": f"🔧 Using tool: {name} (Executor)"}
            
            # Caching Logic
            cache_key = f"{name}:{args_str}"
            if settings.CACHE_ENABLED and cache_key in self.tool_cache:
                Monitoring.log_cache_stats(hit=True)
                result = self.tool_cache[cache_key]
            else:
                Monitoring.log_cache_stats(hit=False)
                result = await self.available_tools.execute(name, args)
                if settings.CACHE_ENABLED:
                    self.tool_cache[cache_key] = result
            
            self.memory.add_message(Message.tool_message(result, name, call.id))
            
            if name == "terminate":
                self.state = AgentState.FINISHED
                yield {"type": "content", "content": result}

    async def reflect_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """CRITIC Phase: Check if previous step was successful or needs correction"""
        if self.state == AgentState.FINISHED:
            return

        yield {"type": "status", "content": "🔧 Using tool: verify (Critic)"}
        
        critic_prompt = "CRITIC: Evaluate the last tool output. Is it sufficient to fulfill the user request or the current sub-task? If not, what is missing? Answer concisely. State 'PROCEED' if okay or provide 'FEEDBACK' for correction."
        
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list() + [{"role": "user", "content": critic_prompt}]
        
        analysis = await self.llm.quick_ask(messages)
        
        if "PROCEED" not in analysis.upper():
            logger.info(f"Critic Feedback: {analysis}")
            self.memory.add_message(Message.system_message(f"Critic Feedback: {analysis}. Please adapt your strategy."))
            yield {"type": "content", "content": f"\n\n> [!NOTE]\n> **Critic Feedback**: {analysis}\n"}
        else:
            # Silent proceed or subtle indicator
            pass

class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Củ-Sen"
    system_prompt: str = """You are Manus-Củ-Sen Advanced, a Multi-Agent Orchestrator.
You mimic the original Manus core algorithm using a Planning-Execution-Critic loop.

VIRTUAL ROLES:
1. MANAGER/PLANNER: Break the goal into logical steps. Think inside <thinking> tags.
2. EXECUTOR: Use the available tools strictly based on the plan.
3. CRITIC/VERIFIER: You will automatically review tool outputs after each step to ensure 'Reward' (accuracy/completeness).

COMMANDS:
- memory_tool: Save/Recall persistent data.
- search_tool / scraper: Gather web tri thức.
- calculator: High-precision math.
- file_ops: Workspace management.
- terminate: Use ONLY when the Critic confirms the goal is 100% met.

Logic: Be autonomous, self-correcting, and highly efficient."""

    def add_tool(self, tool: BaseTool):
        self.available_tools.tool_map[tool.name] = tool
