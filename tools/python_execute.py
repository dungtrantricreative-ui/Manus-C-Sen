import multiprocessing
import sys
from io import StringIO
from typing import Dict, Any
from base_tool import BaseTool

import sys
from io import StringIO
from typing import Dict, Any
from base_tool import BaseTool

class PythonExecute(BaseTool):
    """
    A powerful tool for executing Python code directly on the host machine.
    Variables are PERSISTENT between calls in the same session.
    """
    name: str = "python_execute"
    description: str = "Executes Python code on the host machine. Variables PERSIST between calls."
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
1. **HOST ACCESS**: This runs directly on the local machine. You have access to the file system, network, and all installed libraries.
2. **PERSISTENCE**: Global variables defined in one call are available in the next.
3. **PRINT RESULTS**: Use print() to see output.
"""

    _locals: Dict[str, Any] = {}

    async def execute(self, code: str) -> str:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        output_buffer = StringIO()
        sys.stdout = output_buffer
        sys.stderr = output_buffer
        
        try:
            # Execute in the perspective of the project root
            exec(code, self._locals, self._locals)
            obs = output_buffer.getvalue()
            return obs if obs else "Code executed successfully (no output)."
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
