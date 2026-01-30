import json
import os
from typing import Optional
from datetime import datetime
from base_tool import BaseTool
from config import settings
from loguru import logger

class MemoryTool(BaseTool):
    name: str = "memory_tool"
    description: str = "Save or recall information from persistent memory across sessions."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["save", "recall"], "description": "Whether to save or recall info."},
            "key": {"type": "string", "description": "The label or key for the information."},
            "value": {"type": "string", "description": "The information to save (for save action)."}
        },
        "required": ["action", "key"]
    }

    def _load_memory(self) -> dict:
        if os.path.exists(settings.MEMORY_FILE):
            try:
                with open(settings.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memory file: {e}")
        return {}

    def _save_memory_data(self, data: dict):
        try:
            with open(settings.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save memory file: {e}")

    async def execute(self, action: str, key: str, value: Optional[str] = None) -> str:
        memory = self._load_memory()
        
        if action == "save":
            memory[key] = {
                "content": value,
                "timestamp": datetime.now().isoformat()
            }
            self._save_memory_data(memory)
            return f"Information saved under key '{key}'."
            
        elif action == "recall":
            if key in memory:
                info = memory[key]
                return f"Memory for '{key}' (saved at {info['timestamp']}): {info['content']}"
            else:
                return f"No memory found for key '{key}'."
                
        return f"Error: Unknown action '{action}'."
