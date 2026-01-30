import asyncio
from typing import Any
from base_tool import BaseTool

class AskHumanTool(BaseTool):
    name: str = "ask_human"
    description: str = "Ask the human user for clarification, permission, or help when you are stuck or need specific information."
    parameters: dict = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question or prompt to show the user."
            }
        },
        "required": ["question"]
    }

    async def execute(self, question: str) -> str:
        print(f"\n\033[95m🤖 AI Question: {question}\033[0m")
        # Since we are in an async loop, we use to_thread to keep input() from blocking the whole event loop
        # though for this simple CLI it might not matter much, it's safer.
        response = await asyncio.to_thread(input, "📝 Your Response: ")
        return response
