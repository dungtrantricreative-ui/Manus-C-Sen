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
from event_bus import EventBus
from base_tool import ToolResult, BaseTool


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

class LLM:
    def __init__(self):
        # Primary Client
        self.primary_client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL
        )
        # Dynamic Backup Clients - only load those that support tools
        self.backup_clients = []
        for b in settings.BACKUPS:
            if b.api_key and b.supports_tools:  # Filter by tool support
                self.backup_clients.append({
                    "name": b.name,
                    "client": AsyncOpenAI(api_key=b.api_key, base_url=b.base_url),
                    "model": b.model_name
                })

        if self.backup_clients:
            logger.info(f"Loaded {len(self.backup_clients)} backup provider(s): {', '.join([b['name'] for b in self.backup_clients])}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def ask_tool_stream(self, messages: List[dict], tools: List[dict], model: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        # Try primary first
        try:
            response = await self.primary_client.chat.completions.create(
                model=model or settings.MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True
            )
            async for chunk in response:
                yield chunk
            return # Success
        except Exception as e:
            if not self.backup_clients or not any(x in str(e).lower() for x in ["429", "rate limit", "timeout", "connection"]):
                raise e
            logger.debug(f"Primary LLM failed: {e}. Starting failover sequence...")

        # Try backups in order
        for b in self.backup_clients:
            try:
                logger.debug(f"Trying backup provider: {b['name']}")
                response = await b["client"].chat.completions.create(
                    model=b["model"],
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    stream=True
                )
                async for chunk in response:
                    yield chunk
                return # Success
            except Exception as be:
                logger.warning(f"Backup {b['name']} failed: {be}")
                if "bad_request" in str(be).lower():
                    logger.error(f"BAD REQUEST DETAILS: {be}")
                continue
        
        raise Exception("All LLM providers (Primary and Backups) failed.")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def ask_tool(self, messages: List[dict], tools: List[dict], tool_choice: str = "auto") -> Any:
        """Non-streaming tool call - better compatibility with Gemini/DeepSeek"""
        try:
            response = await self.primary_client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                stream=False
            )
            return response.choices[0].message
        except Exception as e:
            if not self.backup_clients or not any(x in str(e).lower() for x in ["429", "rate limit", "timeout", "connection"]):
                raise e
            logger.debug(f"Primary ask_tool failed: {e}")
        
        for b in self.backup_clients:
            try:
                logger.debug(f"Trying backup: {b['name']}")
                response = await b["client"].chat.completions.create(
                    model=b["model"],
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    stream=False
                )
                return response.choices[0].message
            except Exception as be:
                logger.warning(f"Backup {b['name']} failed: {be}")
                if "bad_request" in str(be).lower():
                    logger.error(f"BAD REQUEST DETAILS: {be}")
                continue
        
        raise Exception("All providers failed for ask_tool.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def quick_ask(self, messages: List[dict], max_tokens: int = 200, model: Optional[str] = None) -> str:
        """Sequential failover for quick reflection calls"""
        try:
            response = await self.primary_client.chat.completions.create(
                model=model or settings.MODEL_NAME,
                messages=messages,
                max_tokens=max_tokens,
                stream=False
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if not self.backup_clients or not any(x in str(e).lower() for x in ["429", "rate limit", "timeout", "connection"]):
                raise e
            logger.debug(f"Primary quick_ask failed: {e}. Starting failover sequence...")

        for b in self.backup_clients:
            try:
                logger.debug(f"Trying backup provider (quick_ask): {b['name']}")
                response = await b["client"].chat.completions.create(
                    model=b["model"],
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=False
                )
                return response.choices[0].message.content or ""
            except Exception as be:
                logger.warning(f"Backup {b['name']} quick_ask failed: {be}")
                continue

        raise Exception("All LLM providers failed for quick_ask.")

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

    def trim_memory(self, max_messages: int = 15):
        """Keep system prompt, initial user request, and last N messages"""
        if len(self.memory.messages) <= max_messages:
            return
        
        # Always keep the first message (usually the user's primary request)
        retained = [self.memory.messages[0]]
        # Keep the last N-1 messages
        retained.extend(self.memory.messages[-(max_messages - 1):])
        self.memory.messages = retained
        logger.debug(f"Trimmed memory to {len(self.memory.messages)} messages.")

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
                    # Skip critic for simple tools (search, calculator) to save cost
                    last_tool = self.tool_calls[0].function.name if self.tool_calls else ""
                    if last_tool not in self.simple_tools:
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
    simple_tools: List[str] = Field(default_factory=lambda: ["search_tool", "calculator", "scraper", "planning", "terminate", "transcribe", "browser"])  # Skip critic for these

    async def step_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list()
        
        yield {"type": "status", "content": "🔧 thinking"}
        await EventBus.publish("thinking", f"Thinking... (Step {self.current_step})")

        
        # Use non-streaming for tool calls (OpenManus approach)
        response = await self.llm.ask_tool(messages, self.available_tools.to_params())
        
        # Aggressive sanitization of LLM content response
        from schema import sanitize_content
        content = sanitize_content(response.content) if response.content else ""
        
        if content:
            yield {"type": "content", "content": content}
        
        # Parse tool calls
        self.tool_calls = [ToolCall(**{
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
        }) for tc in (response.tool_calls or [])]
        
        assistant_msg = Message.from_tool_calls(self.tool_calls, content=content) if self.tool_calls else Message.assistant_message(content)
        self.memory.add_message(assistant_msg)
        
        if not self.tool_calls:
            self.state = AgentState.FINISHED
            return

        # 2. EXECUTOR Phase
        for call in self.tool_calls:
            name = call.function.name
            args_str = call.function.arguments
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tool arguments: {args_str}")
                error_msg = f"Error: Invalid JSON arguments provided for tool {name}."
                self.memory.add_message(Message.tool_message(error_msg, name, call.id))
                yield {"type": "content", "content": error_msg}
                continue
            
            yield {"type": "status", "content": f"🔧 Using tool: {name} (Executor)"}
            await EventBus.publish("terminal", f"> Executing {name} with args: {args_str}")

            
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
            
            # Surgical Truncation to prevent BadRequest (400) context overflow
            # We keep the first 4000 and last 4000 characters to preserve context markers and error results
            max_result_len = 10000 
            if len(str(result)) > max_result_len:
                original_len = len(str(result))
                res_str = str(result)
                result = res_str[:4000] + f"\n\n... [TRUNCATED {original_len - 8000} CHARS] ...\n\n" + res_str[-4000:]
                logger.info(f"Advanced surgical head/tail truncation applied to {name} output.")

            self.memory.add_message(Message.tool_message(result, name, call.id))
            
            if name == "terminate":
                self.state = AgentState.FINISHED
                yield {"type": "content", "content": result}

    async def reflect_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """CRITIC Phase: Check if previous step was successful or needs correction"""
        if self.state == AgentState.FINISHED:
            return

        yield {"type": "status", "content": "🔧 Using tool: verify (Critic)"}

        
        critic_prompt = "CRITIC: Analyze the tool output. Is it enough? Answer ONLY with 'PROCEED' or a short 'FEEDBACK: [what is missing]'. DO NOT output code, JSON, or tool calls."
        
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory.to_dict_list() + [{"role": "user", "content": critic_prompt}]
        
        analysis_raw = await self.llm.quick_ask(messages)
        # Absolute Sanitization + Length Limit (Phase 10)
        from schema import sanitize_content
        analysis = sanitize_content(analysis_raw)
        if len(analysis) > 500:
            analysis = analysis[:500] + "... [TRUNCATED]"

        if "PROCEED" not in analysis.upper():
            last_tool = self.tool_calls[0].function.name if self.tool_calls else ""
            failover_msg = ""
            if last_tool == "search" and ("FEEDBACK" in analysis.upper() or "NOT ENOUGH" in analysis.upper()):
                failover_msg = " [FAILOVER HINT: Search results poor. Use 'browser' with go_to_url to get deeper info.]"
            
            logger.info(f"Critic Feedback: {analysis}{failover_msg}")
            # Use USER message for feedback - more compatible with strict providers
            self.memory.add_message(Message.user_message(f"Critic Feedback: {analysis}{failover_msg}"))
            yield {"type": "content", "content": f"\n\n> [!TIP]\n> **Critic Feedback**: {analysis}{failover_msg}\n"}
        else:
            # Silent proceed or subtle indicator
            pass

class ManusCompetition(ToolCallAgent):
    name: str = "Manus-Củ-Sen"
    system_prompt: str = """You are Manus-Củ-Sen ULTIMATE, the supreme autonomous AI agent.
You operate under the "Manus Architecture": Structured Planning -> Execution -> Critic.

AUTONOMOUS CORE PRINCIPLES:
1. PLAN FIRST: For ANY non-trivial request, your VERY FIRST tool call MUST be `planning(command='create', ...)`.
2. MANDATORY COMPLETION: Once a plan is created, you MUST NOT stop until EVERY STEP is completed or a failure is reported via `terminate`. 
3. NO CHATTER: Do not give long summaries in chat if the user asked for a file. Deliver the file, then say it's done. 
4. NEVER Hallucinate Paths: Use file paths EXACTLY as provided. Wrap in double quotes for terminal commands.
5. SUPREME PERSISTENCE: If a tool fails, investigate using 'terminal' (dir/ls). Do not give up.

STRICT EXECUTION PROTOCOL:
1. ANALYZE & PLAN: Identify goals. Create a structured plan immediately.
2. EXECUTE: Follow your plan steps. Use 'browser' for web, 'transcribe' for audio, and 'terminal' for system tasks.
3. CRITIC: Self-correct if a step fails.

COMMANDS:
- planning: MANDATORY first step.
- terminal: Use for system tasks. NEVER use 'uv run', use direct 'python' or 'pip'. 
- search_tool: Quick web search.
- browser: Deep web interaction.
- transcribe: Audio to text.
- terminate: Use only when the goal is achieved or impossible.
"""
    def add_tool(self, tool: BaseTool):
        self.available_tools.tool_map[tool.name] = tool
