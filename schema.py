from enum import Enum
from typing import Any, List, Literal, Optional, Union, Dict
from pydantic import BaseModel, Field

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class AgentState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"

class ToolChoice(str, Enum):
    """Tool choice options"""
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"

class Function(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Function

class Message(BaseModel):
    role: Role
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    base64_image: Optional[str] = None

    def to_dict(self) -> dict:
        msg = {"role": self.role.value if isinstance(self.role, Role) else self.role}
        if self.content is not None: msg["content"] = self.content
        if self.tool_calls: msg["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        if self.name: msg["name"] = self.name
        if self.tool_call_id: msg["tool_call_id"] = self.tool_call_id
        if self.base64_image: msg["base64_image"] = self.base64_image
        return msg

    @classmethod
    def user_message(cls, content: str, base64_image: Optional[str] = None) -> "Message":
        return cls(role=Role.USER, content=content, base64_image=base64_image)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None) -> "Message":
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool_message(cls, content: str, name: str, tool_call_id: str) -> "Message":
        return cls(role=Role.TOOL, content=content, name=name, tool_call_id=tool_call_id)

class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = 100
    _summary_threshold: int = 20

    def add_message(self, message: Message):
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    async def summarize(self, llm: Any):
        """Summarize old messages to save tokens if history is too long."""
        # Only summarize if we are over the threshold and not just summarizing a summary
        if len(self.messages) <= self._summary_threshold:
            return

        # Keep system prompt (index 0 usually) and the last 5 messages
        # Summarize everything in between
        num_to_summarize = len(self.messages) - 10
        if num_to_summarize <= 5:
            return

        from loguru import logger
        logger.success(f"🧠 Performance: Optimizing context ({num_to_summarize} messages)...")
        
        system_prompt = self.messages[0] if self.messages[0].role == Role.SYSTEM else None
        start_idx = 1 if system_prompt else 0
        to_summarize = self.messages[start_idx : start_idx + num_to_summarize]
        
        # Format for LLM
        summary_input = "\n".join([f"{m.role}: {m.content[:500]}" for m in to_summarize if m.content])
        prompt = f"Please provide a concise summary of the following conversation history. Focus on: 1. The original goal. 2. Key findings/data. 3. Current status. \n\n{summary_input}"
        
        try:
            # Use quick_ask if available on LLM
            summary_text = await llm.quick_ask([{"role": "user", "content": prompt}])
            if summary_text:
                summary_msg = Message.system_message(f"--- CONTEXT SUMMARY ---\n{summary_text}\n--- END SUMMARY ---")
                
                # Reconstruct messages: [System] + [Summary] + [Last 5-10 messages]
                new_messages = []
                if system_prompt:
                    new_messages.append(system_prompt)
                new_messages.append(summary_msg)
                new_messages.extend(self.messages[start_idx + num_to_summarize:])
                
                self.messages = new_messages
                logger.success("✅ Context optimized.")
        except Exception as e:
            logger.warning(f"Failed to summarize context: {e}")

    def to_dict_list(self) -> List[dict]:
        return [m.to_dict() for m in self.messages]
