import sys
import io
import contextlib
from agent_core import BaseTool
from loguru import logger

class PythonREPLTool(BaseTool):
    name: str = "python_repl"
    description: str = "Execute Python code for calculations, data processing, or algorithms. Use this when math or logic is too complex for text."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The Python code to execute."}
        },
        "required": ["code"]
    }

    async def execute(self, code: str) -> str:
        """Executes the given python code and returns the captured stdout."""
        logger.info(f"Executing Python code...")
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            try:
                exec(code, globals())
            except Exception as e:
                return f"Error executing code: {str(e)}"
        
        output = f.getvalue()
        return output if output else "Code executed successfully (no output)."
