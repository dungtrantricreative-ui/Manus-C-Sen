from typing import Dict, List, Literal, Optional
from base_tool import BaseTool
from pydantic import Field

class PlanningTool(BaseTool):
    name: str = "planning"
    description: str = """A planning tool to create and manage structured plans for complex tasks.
    Use this once at the beginning of a task to outline steps, and then use it to mark steps as completed."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Operation: 'create' (new plan), 'mark_step' (update status), or 'get' (view plan).",
                "enum": ["create", "mark_step", "get"]
            },
            "title": {
                "type": "string",
                "description": "Title for a new plan (required for 'create')."
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of steps (required for 'create')."
            },
            "step_index": {
                "type": "integer",
                "description": "Index of the step (0-based, for 'mark_step')."
            },
            "step_status": {
                "type": "string",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "description": "New status for the step."
            }
        },
        "required": ["command"]
    }

    # Storage for the current session plan
    current_plan: Dict = Field(default_factory=dict)

    async def execute(self, command: str, **kwargs) -> str:
        if command == "create":
            title = kwargs.get("title", "Untitled Task")
            steps = kwargs.get("steps", [])
            if not steps:
                return "Error: 'steps' list is required to create a plan."
            
            self.current_plan = {
                "title": title,
                "steps": steps,
                "statuses": ["not_started"] * len(steps)
            }
            return f"Plan Created: {title}\n" + self._format_plan()

        elif command == "get":
            if not self.current_plan:
                return "No plan currently exists."
            return self._format_plan()

        elif command == "mark_step":
            if not self.current_plan:
                return "Error: No plan exists to update."
            
            idx = kwargs.get("step_index")
            status = kwargs.get("step_status", "completed")
            
            if idx is None or not (0 <= idx < len(self.current_plan["steps"])):
                return f"Error: Invalid step_index {idx}."
            
            self.current_plan["statuses"][idx] = status
            return f"Step {idx} updated to {status}.\n" + self._format_plan()

        return f"Unknown command: {command}"

    def _format_plan(self) -> str:
        plan = self.current_plan
        output = f"\n📋 **PLAN: {plan['title']}**\n"
        output += "=" * 30 + "\n"
        
        symbols = {
            "not_started": "[ ]",
            "in_progress": "[→]",
            "completed": "[✓]",
            "blocked": "[!]"
        }
        
        for i, (step, status) in enumerate(zip(plan["steps"], plan["statuses"])):
            sym = symbols.get(status, "[ ]")
            output += f"{i}. {sym} {step}\n"
        
        output += "=" * 30 + "\n"
        return output
