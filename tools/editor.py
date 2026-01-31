import os
from typing import Any, Dict, List, Literal, Optional
from base_tool import BaseTool, ToolResult

class EditorTool(BaseTool):
    """
    Custom editing tool for viewing, creating and editing files.
    Inspired by OpenManus StrReplaceEditor.
    """
    name: str = "editor"
    description: str = """Custom editing tool for viewing, creating and editing files.
    * Use 'view' to see file content with line numbers.
    * Use 'create' to make a new file.
    * Use 'str_replace' to replace a UNIQUE string with new text.
    * Use 'insert' to insert text after a specific line.
    * Use 'undo' to revert the last edit.
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["view", "create", "str_replace", "insert", "undo"],
                "description": "The command to run."
            },
            "path": {
                "type": "string",
                "description": "Absolute path to the file."
            },
            "file_text": {
                "type": "string",
                "description": "Content for 'create' command."
            },
            "old_str": {
                "type": "string",
                "description": "Unique string to replace (for 'str_replace')."
            },
            "new_str": {
                "type": "string",
                "description": "New string to put (for 'str_replace' or 'insert')."
            },
            "insert_line": {
                "type": "integer",
                "description": "Line number to insert AFTER (for 'insert')."
            },
            "view_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Line range [start, end] for 'view'. Use [1, -1] for all."
            }
        },
        "required": ["command", "path"]
    }

    # Simplified history: path -> list of previous contents
    _history: Dict[str, List[str]] = {}

    async def execute(self, command: str, path: str, **kwargs) -> str:
        path = self._sanitize_path(path)
        path = os.path.abspath(path)
        
        if command == "view":
            return await self._view(path, kwargs.get("view_range"))
        elif command == "create":
            return await self._create(path, kwargs.get("file_text", ""))
        elif command == "str_replace":
            return await self._str_replace(path, kwargs.get("old_str", ""), kwargs.get("new_str", ""))
        elif command == "insert":
            return await self._insert(path, kwargs.get("insert_line"), kwargs.get("new_str", ""))
        elif command == "undo":
            return await self._undo(path)
        
        return f"Error: Unknown command '{command}'"

    def _sanitize_path(self, path: str) -> str:
        """Safety net: Redirect stray or hallucinated paths to outputs/"""
        # If it's a Linux hallucination like /tmp/ or /home/
        if path.startswith('/') or path.startswith('~'):
             filename = os.path.basename(path)
             return os.path.join("outputs", filename)
        
        # If it's a simple relative path without 'outputs/' prefix
        if not os.path.isabs(path) and not path.startswith("outputs") and not path.startswith("tools") and not path.startswith("knowledge"):
             return os.path.join("outputs", path)
             
        return path

    async def _view(self, path: str, view_range: Optional[List[int]]) -> str:
        if not os.path.exists(path):
            return f"Error: File not found at {path}"
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            start, end = 1, len(lines)
            if view_range and len(view_range) == 2:
                start = max(1, view_range[0])
                end = len(lines) if view_range[1] == -1 else min(len(lines), view_range[1])
            
            output = [f"File: {path} (Lines {start}-{end} of {len(lines)})"]
            for i in range(start - 1, end):
                output.append(f"{i+1:6}\t{lines[i].rstrip()}")
            
            return "\n".join(output)
        except Exception as e:
            return f"Error reading file: {str(e)}"

    async def _create(self, path: str, content: str) -> str:
        if os.path.exists(path):
            return f"Error: File already exists at {path}. Use 'str_replace' to edit."
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: File created at {path}"
        except Exception as e:
            return f"Error creating file: {str(e)}"

    async def _str_replace(self, path: str, old_str: str, new_str: str) -> str:
        if not os.path.exists(path): return f"Error: File not found: {path}"
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        count = content.count(old_str)
        if count == 0:
            return f"Error: 'old_str' not found in {path}. Ensure exact match."
        if count > 1:
            return f"Error: 'old_str' appears {count} times. Make it more unique."
        
        # Save to history
        if path not in self._history: self._history[path] = []
        self._history[path].append(content)
        
        new_content = content.replace(old_str, new_content := new_str)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return f"Success: Replaced content in {path}. Use 'view' to check changes."

    async def _insert(self, path: str, line_no: Optional[int], new_str: str) -> str:
        if not os.path.exists(path): return f"Error: File not found: {path}"
        if line_no is None: return "Error: 'insert_line' is required."
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not (0 <= line_no <= len(lines)):
            return f"Error: Line {line_no} out of range (0-{len(lines)})."
        
        # Save to history
        content = "".join(lines)
        if path not in self._history: self._history[path] = []
        self._history[path].append(content)
        
        lines.insert(line_no, new_str + "\n" if not new_str.endswith("\n") else new_str)
        
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return f"Success: Inserted text after line {line_no} in {path}."

    async def _undo(self, path: str) -> str:
        if path not in self._history or not self._history[path]:
            return f"Error: No history to undo for {path}."
        
        old_content = self._history[path].pop()
        with open(path, "w", encoding="utf-8") as f:
            f.write(old_content)
        
        return f"Success: Last edit to {path} reverted."
