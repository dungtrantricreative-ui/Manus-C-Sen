from enum import Enum
from typing import Any, List, Literal, Optional, Union
import re

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role options"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """Tool choice options"""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function


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


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: ROLE_TYPE = Field(...)  # type: ignore
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """Support Message + list or Message + Message"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """Support list + Message"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        
        # Aggressive sanitization of content (Phase 10 Hardening)
        content = sanitize_content(self.content) if self.content else self.content

        # Some providers (Gemini/Llama) crash if content is "" when tool_calls is present
        if self.role == Role.ASSISTANT and self.tool_calls:
            # Force null content for assistant tool calls for maximum compatibility if content is empty/stripped
             if not content:
                message["content"] = None
             else:
                message["content"] = content
        elif content is not None:
             message["content"] = content
             
        if self.tool_calls is not None:
             # Ensure pure format
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
        if self.base64_image is not None:
            # Note: For some providers, base64 might need to be in a specific content list format.
            # But we will stick to OpenManus implementation: keeping it as a field for now or relying on LLM class to format it.
            # OpenManus seems to rely on the LLM class or just having it in the object.
            # However, standard OpenAI API expects image in "content": [{"type": "image_url", ...}]
            # OpenManus LLM class handles this.
            message["base64_image"] = self.base64_image
            
        return message

    @classmethod
    def user_message(
        cls, content: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER, content=content, base64_image=base64_image)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(
        cls, content: Optional[str] = None, base64_image: Optional[str] = None
    ) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content, base64_image=base64_image)

    @classmethod
    def tool_message(
        cls, content: str, name, tool_call_id: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            base64_image=base64_image,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: List[Any],
        content: Union[str, List[str]] = "",
        base64_image: Optional[str] = None,
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls."""
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT,
            content=content or "", # Ensure string
            tool_calls=formatted_calls,
            base64_image=base64_image,
            **kwargs,
        )


class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]
