import multiprocessing
import sys
from io import StringIO
from typing import Dict, Any
from base_tool import BaseTool

class PythonExecute(BaseTool):
    """
    A powerful tool for executing Python code. 
    Ideal for data analysis, math, and string manipulation.
    """
    name: str = "python_execute"
    description: str = "Executes Python code. Use print() to see results. Variables are not persistent between calls."
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
    
    instructions: str = """
1. **PRINT EVERYTHING**: Only printed output is captured. Do not just return values.
2. **SANDBOXED**: Imports are allowed, but external networking might be restricted.
3. **UTILITY**: Use this for complex calculations or data processing that is hard in natural language.
"""

    def _run_code(self, code: str, result_dict: dict, safe_globals: dict) -> None:
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer
            exec(code, safe_globals, safe_globals)
            result_dict["observation"] = output_buffer.getvalue()
            result_dict["success"] = True
        except Exception as e:
            result_dict["observation"] = str(e)
            result_dict["success"] = False
        finally:
            sys.stdout = original_stdout

    async def execute(self, code: str, timeout: int = 10) -> str:
        # Use multiprocessing for isolation and timeout
        with multiprocessing.Manager() as manager:
            result = manager.dict({"observation": "", "success": False})
            
            # Setup builtins
            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}
            
            proc = multiprocessing.Process(
                target=self._run_code, args=(code, result, safe_globals)
            )
            proc.start()
            proc.join(timeout)

            if proc.is_alive():
                proc.terminate()
                proc.join(1)
                return f"Error: Execution timeout after {timeout} seconds"
            
            obs = result.get("observation", "")
            if not result.get("success", False):
                return f"Error: {obs}"
            return obs if obs else "Code executed successfully (no output)."
