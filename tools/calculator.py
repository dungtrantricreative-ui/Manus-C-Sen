import math
import operator
import re
from agent_core import BaseTool
from loguru import logger

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Perform a mathematical calculation safely."
    parameters: dict = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "The math expression to evaluate (e.g., '2 + 2 * 3')."}
        },
        "required": ["expression"]
    }

    async def execute(self, expression: str) -> str:
        # Basic character whitelist for safety
        if not re.match(r"^[0-9+\-*/^().\s]+$", expression):
            return "Error: Expression contains invalid characters."
        
        try:
            # Replace ^ with ** for Python power
            expr = expression.replace("^", "**")
            # Using eval with limited globals for safety
            result = eval(expr, {"__builtins__": None}, {
                "abs": abs, "round": round, "math": math
            })
            return str(result)
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            return f"Error evaluating expression: {str(e)}"
