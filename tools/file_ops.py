import os
from typing import Optional
from base_tool import BaseTool
from loguru import logger

class FileOpsTool(BaseTool):
    name: str = "file_ops"
    description: str = "Perform file operations: read, write, or list files. Supports absolute paths."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "write", "list"], "description": "The action to perform."},
            "filename": {"type": "string", "description": "The name of the file (for read/write)."},
            "content": {"type": "string", "description": "The content to write (for write action)."}
        },
        "required": ["action"]
    }

    async def execute(self, action: str, filename: Optional[str] = None, content: Optional[str] = None) -> str:
        workspace = "." # Default base directory
        
        try:
            if action == "list":
                # If filename is provided for list, use it as directory
                target_dir = filename if filename and os.path.isabs(filename) else workspace
                files = os.listdir(target_dir)
                return f"Files in {target_dir}: {', '.join(files)}" if files else f"Directory {target_dir} is empty."
            
            if not filename:
                return "Error: filename is required for read/write actions."
            
            # Check if filename is an absolute path
            if os.path.isabs(filename):
                file_path = filename
            else:
                file_path = os.path.join(workspace, filename)
            
            if action == "read":
                if not os.path.exists(file_path):
                    return f"Error: File '{filename}' not found."
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            if action == "write":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content or "")
                return f"Successfully wrote to '{filename}'."
                
            return f"Error: Unknown action '{action}'."
        except Exception as e:
            logger.error(f"FileOps error: {e}")
            return f"Error performing file operation: {str(e)}"
