from typing import ClassVar, Dict, List, Literal, Optional
from base_tool import BaseTool
from pydantic import Field

class PlanningTool(BaseTool):
    """
    Advanced Planning tool with auto-decomposition, dependency tracking,
    and feasibility validation for complex task sequences.
    """
    name: str = "planning"
    description: str = """Create and manage structured plans for complex tasks.
    Commands:
    - 'create': Start a new plan with steps. Supports auto-decomposition from a goal.
    - 'update': Change the title or steps of an existing plan.
    - 'mark_step': Update a step's status (completed, in_progress, blocked).
    - 'get': View the full plan with progress and dependencies.
    - 'validate': Check plan feasibility and suggest optimizations.
    - 'next': Get the next actionable step (skips blocked/completed).
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["create", "update", "mark_step", "get", "delete", "validate", "next"],
                "description": "The planning command to execute."
            },
            "title": {
                "type": "string",
                "description": "Title of the plan."
            },
            "goal": {
                "type": "string",
                "description": "High-level goal for auto-decomposition (create command)."
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of steps. If goal is provided, this can be empty for auto-decomposition."
            },
            "step_index": {
                "type": "integer",
                "description": "0-based index of the step to update."
            },
            "step_status": {
                "type": "string",
                "enum": ["not_started", "in_progress", "completed", "blocked", "skipped"],
                "description": "The new status for the step."
            },
            "notes": {
                "type": "string",
                "description": "Optional notes for the step."
            },
            "priority": {
                "type": "integer",
                "description": "Priority level 1-5 (1=highest). Default is 3."
            },
            "depends_on": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Indices of steps this step depends on."
            }
        },
        "required": ["command"]
    }

    current_plan: Dict = Field(default_factory=dict)

    # Templates for auto-decomposition based on common task types (ClassVar = not a Pydantic field)
    DECOMPOSITION_TEMPLATES: ClassVar[Dict[str, List[str]]] = {
        "research": [
            "Define research scope and questions",
            "Search for relevant information",
            "Analyze and synthesize findings",
            "Document conclusions"
        ],
        "build": [
            "Gather requirements and constraints",
            "Design solution architecture",
            "Implement core functionality",
            "Test and validate",
            "Document and finalize"
        ],
        "fix": [
            "Reproduce and understand the issue",
            "Identify root cause",
            "Implement fix",
            "Verify fix works",
            "Prevent regression"
        ],
        "analyze": [
            "Collect relevant data",
            "Process and organize data",
            "Apply analytical methods",
            "Interpret results",
            "Present findings"
        ],
        "default": [
            "Understand the task requirements",
            "Plan approach",
            "Execute main steps",
            "Review and finalize"
        ]
    }

    def _detect_task_type(self, goal: str) -> str:
        """Detect task type from goal description."""
        goal_lower = goal.lower()
        if any(w in goal_lower for w in ["research", "find", "search", "learn", "investigate"]):
            return "research"
        elif any(w in goal_lower for w in ["build", "create", "implement", "develop", "make"]):
            return "build"
        elif any(w in goal_lower for w in ["fix", "debug", "repair", "resolve", "solve"]):
            return "fix"
        elif any(w in goal_lower for w in ["analyze", "examine", "evaluate", "assess"]):
            return "analyze"
        return "default"

    def _auto_decompose(self, goal: str) -> List[str]:
        """Auto-decompose a goal into steps based on task type."""
        task_type = self._detect_task_type(goal)
        template = self.DECOMPOSITION_TEMPLATES[task_type]
        
        # Contextualize template with the goal
        contextualized = []
        for step in template:
            if task_type != "default":
                contextualized.append(f"{step} (for: {goal[:50]}...)" if len(goal) > 50 else f"{step} (for: {goal})")
            else:
                contextualized.append(step)
        
        return contextualized

    async def execute(self, command: str, **kwargs) -> str:
        if command == "create":
            goal = kwargs.get("goal", "")
            steps = kwargs.get("steps", [])
            
            # Auto-decompose if goal provided but no steps
            if goal and not steps:
                steps = self._auto_decompose(goal)
            
            if not steps:
                return "Error: Either 'steps' list or 'goal' for auto-decomposition is required."
            
            self.current_plan = {
                "title": kwargs.get("title", goal or "Main Project"),
                "goal": goal,
                "steps": steps,
                "statuses": ["not_started"] * len(steps),
                "notes": [""] * len(steps),
                "priorities": [kwargs.get("priority", 3)] * len(steps),
                "dependencies": [kwargs.get("depends_on", [])] * len(steps)
            }
            return f"Plan Created: {self.current_plan['title']}\n" + self._format_plan()

        elif command == "update":
            if not self.current_plan:
                return "Error: No plan exists."
            if "title" in kwargs:
                self.current_plan["title"] = kwargs["title"]
            if "steps" in kwargs:
                new_steps = kwargs["steps"]
                diff = len(new_steps) - len(self.current_plan["steps"])
                if diff > 0:
                    self.current_plan["statuses"].extend(["not_started"] * diff)
                    self.current_plan["notes"].extend([""] * diff)
                    self.current_plan["priorities"].extend([3] * diff)
                    self.current_plan["dependencies"].extend([[]] * diff)
                else:
                    for key in ["statuses", "notes", "priorities", "dependencies"]:
                        self.current_plan[key] = self.current_plan[key][:len(new_steps)]
                self.current_plan["steps"] = new_steps
            return f"Plan Updated.\n" + self._format_plan()

        elif command == "mark_step":
            if not self.current_plan:
                return "Error: No active plan."
            idx = kwargs.get("step_index")
            if idx is None or not (0 <= idx < len(self.current_plan["steps"])):
                return f"Error: Invalid index {idx}."
            
            # Check dependencies before marking in_progress or completed
            new_status = kwargs.get("step_status", "")
            if new_status in ["in_progress", "completed"]:
                deps = self.current_plan["dependencies"][idx]
                for dep_idx in deps:
                    if self.current_plan["statuses"][dep_idx] != "completed":
                        return f"Error: Step {idx} depends on step {dep_idx} which is not completed yet."
            
            if "step_status" in kwargs:
                self.current_plan["statuses"][idx] = kwargs["step_status"]
            if "notes" in kwargs:
                self.current_plan["notes"][idx] = kwargs["notes"]
            if "priority" in kwargs:
                self.current_plan["priorities"][idx] = kwargs["priority"]
            if "depends_on" in kwargs:
                self.current_plan["dependencies"][idx] = kwargs["depends_on"]
            
            return f"Step {idx} updated.\n" + self._format_plan()

        elif command == "get":
            if not self.current_plan:
                return "No active plan found."
            return self._format_plan()

        elif command == "validate":
            if not self.current_plan:
                return "No plan to validate."
            return self._validate_plan()

        elif command == "next":
            if not self.current_plan:
                return "No active plan. Use 'create' first."
            return self._get_next_step()

        elif command == "delete":
            self.current_plan = {}
            return "Plan deleted."

        return f"Unknown command: {command}"

    def _validate_plan(self) -> str:
        """Validate plan for issues and suggest optimizations."""
        p = self.current_plan
        issues = []
        suggestions = []
        
        # Check for circular dependencies
        for i, deps in enumerate(p["dependencies"]):
            for dep in deps:
                if dep >= i:
                    issues.append(f"⚠️ Step {i} depends on step {dep} which comes after it.")
                if dep == i:
                    issues.append(f"❌ Step {i} has circular self-dependency.")
        
        # Check for blocked steps with completed dependencies
        for i, (status, deps) in enumerate(zip(p["statuses"], p["dependencies"])):
            if status == "blocked":
                all_deps_done = all(p["statuses"][d] == "completed" for d in deps)
                if all_deps_done:
                    suggestions.append(f"💡 Step {i} is blocked but all dependencies are completed. Consider unblocking.")
        
        # Check for priority imbalances
        high_priority_blocked = [i for i, (s, pr) in enumerate(zip(p["statuses"], p["priorities"])) 
                                  if s == "not_started" and pr <= 2]
        if high_priority_blocked:
            suggestions.append(f"⏰ High priority steps not started: {high_priority_blocked}")
        
        result = "📋 **Plan Validation Report**\n"
        result += "─" * 40 + "\n"
        
        if not issues and not suggestions:
            result += "✅ Plan looks good! No issues found.\n"
        else:
            if issues:
                result += "**Issues:**\n" + "\n".join(issues) + "\n"
            if suggestions:
                result += "**Suggestions:**\n" + "\n".join(suggestions) + "\n"
        
        # Progress summary
        completed = p["statuses"].count("completed")
        total = len(p["steps"])
        result += f"\n📊 Progress: {completed}/{total} ({completed/total*100:.0f}%)\n"
        
        return result

    def _get_next_step(self) -> str:
        """Get the next actionable step."""
        p = self.current_plan
        
        # First, check for in-progress steps
        for i, status in enumerate(p["statuses"]):
            if status == "in_progress":
                return f"🔵 Currently working on Step {i}: {p['steps'][i]}"
        
        # Find next actionable step (respecting dependencies and priority)
        actionable = []
        for i, (status, deps) in enumerate(zip(p["statuses"], p["dependencies"])):
            if status == "not_started":
                # Check if all dependencies are completed
                deps_met = all(p["statuses"][d] == "completed" for d in deps) if deps else True
                if deps_met:
                    actionable.append((i, p["priorities"][i]))
        
        if not actionable:
            if all(s == "completed" for s in p["statuses"]):
                return "🎉 All steps completed! Plan finished."
            return "⏸️ No actionable steps. Some may be blocked by dependencies."
        
        # Sort by priority (lower number = higher priority)
        actionable.sort(key=lambda x: x[1])
        next_idx = actionable[0][0]
        
        return f"➡️ Next step (#{next_idx}): {p['steps'][next_idx]}\n   Priority: {p['priorities'][next_idx]}, Dependencies: {p['dependencies'][next_idx] or 'None'}"

    def _format_plan(self) -> str:
        p = self.current_plan
        steps = p["steps"]
        stats = p["statuses"]
        notes = p["notes"]
        priorities = p.get("priorities", [3] * len(steps))
        deps = p.get("dependencies", [[] for _ in steps])
        
        completed = stats.count("completed")
        total = len(steps)
        percent = (completed / total * 100) if total > 0 else 0
        
        output = f"\n📋 **{p['title']}** [{completed}/{total} - {percent:.0f}%]\n"
        if p.get("goal"):
            output += f"🎯 Goal: {p['goal']}\n"
        output += "─" * 40 + "\n"
        
        symbols = {
            "not_started": "⚪",
            "in_progress": "🔵",
            "completed": "🟢",
            "blocked": "🔴",
            "skipped": "⏭️"
        }
        
        priority_labels = {1: "🔥", 2: "⚡", 3: "", 4: "📉", 5: "📉📉"}
        
        for i, (text, status, note, pri, dep) in enumerate(zip(steps, stats, notes, priorities, deps)):
            sym = symbols.get(status, "⚪")
            pri_sym = priority_labels.get(pri, "")
            dep_info = f" (deps: {dep})" if dep else ""
            output += f"{i}. {sym} {pri_sym}{text}{dep_info}\n"
            if note:
                output += f"   └ 📝 {note}\n"
        
        output += "─" * 40 + "\n"
        return output
