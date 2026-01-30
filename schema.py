import re
from enum import Enum
from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]

def sanitize_content(text: str) -> str:
    """Strip all internal LLM control tokens to prevent 400 Bad Request errors."""
    if not text:
        return text
    # Strip common control tokens: <|...|>, [INST], [/INST], etc.
    patterns = [
        r"<\|.*?\|>",  # Llama-3, ChatML, etc.
        r"\[/?INST\]",  # Llama-2
        r"<<SYS>>",     # Llama-2 system
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<|end_header_id|>",
        r"<|start_header_id|>"
    ]
    sanitized = text
    for p in patterns:
        sanitized = re.sub(p, "", sanitized)
    return sanitized.strip()

class ToolChoice(str, Enum):
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"

TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]

class AgentState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"

class Function(BaseModel):
    name: str
    arguments: str

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Function

class Message(BaseModel):
    role: ROLE_TYPE = Field(...)
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)

    def to_dict(self) -> dict:
        message = {"role": self.role}
        
        # Aggressive sanitization of content
        content = sanitize_content(self.content) if self.content else self.content

        # Some providers (Gemini/Llama) crash if content is "" when tool_calls is present
        if self.role == Role.ASSISTANT and self.tool_calls:
            # Force null content for assistant tool calls for maximum compatibility
            message["content"] = None
        elif content is not None:
             message["content"] = content
             
        if self.tool_calls is not None:
            # Ensure tool calls are in the pure format expected by OpenAI-like APIs
            # Stripping any extra fields that Pydantic might add
            serialized_calls = []
            for tc in self.tool_calls:
                call_dict = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                serialized_calls.append(call_dict)
            message["tool_calls"] = serialized_calls
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str) -> "Message":
        return cls(role=Role.USER, content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        return cls(role=Role.ASSISTANT, content=content)

    @classmethod
    def tool_message(cls, content: str, name: str, tool_call_id: str) -> "Message":
        return cls(role=Role.TOOL, content=content, name=name, tool_call_id=tool_call_id)

    @classmethod
    def from_tool_calls(cls, tool_calls: List[Any], content: str = ""):
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(role=Role.ASSISTANT, content=content, tool_calls=formatted_calls)

class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def to_dict_list(self) -> List[dict]:
        return [msg.to_dict() for msg in self.messages]
