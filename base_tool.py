from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Dict, List
from abc import ABC, abstractmethod

class ToolResult(BaseModel):
    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    def __str__(self):
        return f"Error: {self.error}" if self.error else str(self.output)

class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
    pass

class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""
    pass

class BaseTool(ABC, BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str
    description: str
    parameters: Optional[dict] = None
    instructions: Optional[str] = None  # Specific expert guidelines for this tool

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
    """A collection of defined tools."""

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> List[Dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    async def execute(self, *, name: str, tool_input: Dict[str, Any] = None) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolResult(error=f"Tool {name} is invalid")
        try:
            result = await tool.execute(**(tool_input or {}))
            return result
        except Exception as e:
            return ToolResult(error=str(e))

    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    def add_tools(self, *tools: BaseTool):
        self.tools += tools
        for tool in tools:
            self.tool_map[tool.name] = tool
