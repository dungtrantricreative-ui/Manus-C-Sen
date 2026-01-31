from base_tool import BaseTool, ToolResult

class Terminate(BaseTool):
    name: str = "terminate"
    description: str = "Terminate the conversation with a final answer. Use this when you have completed the user's request or if you are stuck."
    parameters: dict = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The final answer to the user's request. Include all necessary details.",
            }
        },
        "required": ["answer"],
    }

    async def execute(self, answer: str) -> ToolResult:
        # The agent loop should check for this tool call and stop.
        # This execution just returns the answer.
        return ToolResult(output=f"Task Completed. Final Answer: {answer}")
