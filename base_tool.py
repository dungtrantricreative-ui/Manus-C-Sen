from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from abc import ABC, abstractmethod

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
