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
        # Styled output for CLI
        print(f"\n\033[1;35mCAU HOI TU AI:\033[0m \033[35m{question}\033[0m")
        # Since we are in an async loop, we use to_thread to keep input() from blocking the whole event loop
        response = await asyncio.to_thread(input, "\033[1;32mTRA LOI CUA BAN:\033[0m ")
        return response
