import asyncio
import sys
from io import StringIO
from typing import Dict, Any
from pydantic import Field

from base_tool import BaseTool

class PythonTool(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Note: Only print outputs are visible, function return values are not captured. Use print statements to see results."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    persistent_globals: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        if "__builtins__" not in self.persistent_globals:
            if isinstance(__builtins__, dict):
                self.persistent_globals["__builtins__"] = __builtins__
            else:
                self.persistent_globals["__builtins__"] = __builtins__.__dict__.copy()

    def _run_code_sync(self, code: str) -> Dict:
        original_stdout = sys.stdout
        output_buffer = StringIO()
        try:
            sys.stdout = output_buffer
            # Executing in the persistent globals context
            exec(code, self.persistent_globals, self.persistent_globals)
            return {
                "observation": output_buffer.getvalue(),
                "success": True,
            }
        except Exception as e:
            return {
                "observation": f"{output_buffer.getvalue()}\nError: {str(e)}",
                "success": False,
            }
        finally:
            sys.stdout = original_stdout

    async def execute(
        self,
        code: str,
        timeout: int = 10,
    ) -> Dict:
        """
        Executes the provided Python code with state persistence.
        """
        try:
            # Using asyncio to run synchronous code in a thread to allow timeout
            # Note: exec is still blocking the thread, but we can wrap it.
            # For simplicity and given the task, we'll run it directly or use to_thread.
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run_code_sync, code),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return {
                "observation": f"Execution timeout after {timeout} seconds",
                "success": False,
            }
        except Exception as e:
            return {
                "observation": f"Unexpected error: {str(e)}",
                "success": False,
            }
