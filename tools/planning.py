import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from base_tool import BaseTool, ToolResult

class TaskNode(BaseModel):
    id: int
    task: str
    status: str = "pending" # pending, in_progress, completed, failed
    notes: Optional[str] = None

class PlanningTool(BaseTool):
    """
    A Plandex-style planning tool to manage complex objectives.
    Maintains a ledger of atomic sub-tasks.
    """
    name: str = "planning"
    description: str = "Manage the master plan and sub-tasks for complex objectives."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "list", "mark_complete", "reset"],
                "description": "The planning action to perform"
            },
            "tasks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of task descriptions (for 'create' action)"
            },
            "task_id": {
                "type": "integer",
                "description": "ID of the task to update"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "failed"],
                "description": "New status for the task"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes/findings for the task"
            }
        },
        "required": ["action"]
    }

    plan: List[TaskNode] = Field(default_factory=list)

    async def execute(self, action: str, tasks: Optional[List[str]] = None, task_id: Optional[int] = None, status: Optional[str] = None, notes: Optional[str] = None, **kwargs) -> ToolResult:
        if action == "create":
            if not tasks:
                return ToolResult(error="Must provide 'tasks' list for 'create' action.")
            self.plan = [TaskNode(id=i+1, task=t) for i, t in enumerate(tasks)]
            return ToolResult(output=f"Plan created with {len(self.plan)} tasks.\n{self._format_plan()}")

        elif action == "list":
            return ToolResult(output=f"Current Plan:\n{self._format_plan() if self.plan else 'No plan active.'}")

        elif action == "update":
            if task_id is None:
                return ToolResult(error="Must provide 'task_id' for 'update' action.")
            for node in self.plan:
                if node.id == task_id:
                    if status: node.status = status
                    if notes: node.notes = notes
                    return ToolResult(output=f"Task {task_id} updated.\n{self._format_plan()}")
            return ToolResult(error=f"Task ID {task_id} not found.")

        elif action == "mark_complete":
            if task_id is None:
                return ToolResult(error="Must provide 'task_id'.")
            return await self.execute(action="update", task_id=task_id, status="completed")

        elif action == "reset":
            self.plan = []
            return ToolResult(output="Plan cleared.")

        return ToolResult(error=f"Unknown action: {action}")

    def _format_plan(self) -> str:
        lines = []
        for node in self.plan:
            marker = "[ ]"
            if node.status == "in_progress": marker = "[/]"
            elif node.status == "completed": marker = "[x]"
            elif node.status == "failed": marker = "[!]"
            
            line = f"{node.id}. {marker} {node.task}"
            if node.notes:
                line += f" (Notes: {node.notes})"
            lines.append(line)
        return "\n".join(lines)
