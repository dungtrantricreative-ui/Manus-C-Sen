from base_tool import BaseTool, ToolResult

class Terminate(BaseTool):
    name: str = "terminate"
    description: str = "Use this tool to end the task and provide the final answer to the user."
    parameters: dict = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The final answer or summary of the completed task."
            }
        },
        "required": ["answer"]
    }

    async def execute(self, answer: str) -> ToolResult:
        return ToolResult(output=answer)
