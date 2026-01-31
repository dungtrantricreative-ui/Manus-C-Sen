from typing import Dict, List, Literal, Optional
from base_tool import BaseTool
from pydantic import Field

class PlanningTool(BaseTool):
    """
    Advanced Planning tool for managing complex task sequences.
    Optimized for better tracking and progress visualization.
    """
    name: str = "planning"
    description: str = """Create and manage structured plans for complex tasks.
    Commands:
    - 'create': Start a new plan with steps.
    - 'update': Change the title or steps of an existing plan.
    - 'mark_step': Update a step's status (completed, in_progress, etc).
    - 'get': View the full plan and progress.
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["create", "update", "mark_step", "get", "delete"],
                "description": "The planning command to execute."
            },
            "title": {
                "type": "string",
                "description": "Title of the plan."
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of strings representing steps."
            },
            "step_index": {
                "type": "integer",
                "description": "0-based index of the step to update."
            },
            "step_status": {
                "type": "string",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "description": "The new status for the step."
            },
            "notes": {
                "type": "string",
                "description": "Optional notes for the step."
            }
        },
        "required": ["command"]
    }

    current_plan: Dict = Field(default_factory=dict)

    async def execute(self, command: str, **kwargs) -> str:
        if command == "create":
            steps = kwargs.get("steps", [])
            if not steps: return "Error: 'steps' list is required."
            self.current_plan = {
                "title": kwargs.get("title", "Main Project"),
                "steps": steps,
                "statuses": ["not_started"] * len(steps),
                "notes": [""] * len(steps)
            }
            return f"Plan Created: {self.current_plan['title']}\n" + self._format_plan()

        elif command == "update":
            if not self.current_plan: return "Error: No plan exists."
            if "title" in kwargs: self.current_plan["title"] = kwargs["title"]
            if "steps" in kwargs:
                new_steps = kwargs["steps"]
                # Grow or shrink statuses/notes to match
                diff = len(new_steps) - len(self.current_plan["steps"])
                if diff > 0:
                    self.current_plan["statuses"].extend(["not_started"] * diff)
                    self.current_plan["notes"].extend([""] * diff)
                else:
                    self.current_plan["statuses"] = self.current_plan["statuses"][:len(new_steps)]
                    self.current_plan["notes"] = self.current_plan["notes"][:len(new_steps)]
                self.current_plan["steps"] = new_steps
            return f"Plan Updated.\n" + self._format_plan()

        elif command == "mark_step":
            if not self.current_plan: return "Error: No active plan."
            idx = kwargs.get("step_index")
            if idx is None or not (0 <= idx < len(self.current_plan["steps"])):
                return f"Error: Invalid index {idx}."
            
            if "step_status" in kwargs:
                self.current_plan["statuses"][idx] = kwargs["step_status"]
            if "notes" in kwargs:
                self.current_plan["notes"][idx] = kwargs["notes"]
            
            return f"Step {idx} updated.\n" + self._format_plan()

        elif command == "get":
            if not self.current_plan: return "No active plan found."
            return self._format_plan()

        elif command == "delete":
            self.current_plan = {}
            return "Plan deleted."

        return f"Unknown command: {command}"

    def _format_plan(self) -> str:
        p = self.current_plan
        steps = p["steps"]
        stats = p["statuses"]
        notes = p["notes"]
        
        completed = stats.count("completed")
        total = len(steps)
        percent = (completed / total * 100) if total > 0 else 0
        
        output = f"\n📋 **{p['title']}** [{completed}/{total} - {percent:.0f}%]\n"
        output += "─" * 40 + "\n"
        
        symbols = {
            "not_started": "⚪",
            "in_progress": "🔵",
            "completed": "🟢",
            "blocked": "🔴"
        }
        
        for i, (text, status, note) in enumerate(zip(steps, stats, notes)):
            sym = symbols.get(status, "⚪")
            output += f"{i}. {sym} {text}\n"
            if note:
                output += f"   └ 📝 {note}\n"
        
        output += "─" * 40 + "\n"
        return output
