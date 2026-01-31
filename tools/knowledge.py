import os
import json
from typing import List, Optional, Dict
from base_tool import BaseTool

class KnowledgeTool(BaseTool):
    """
    Persistent Knowledge Base tool to store and retrieve successful solutions.
    Helps save tokens and solve recurring tasks faster.
    """
    name: str = "knowledge"
    description: str = """Manage the agent's local knowledge base.
    Commands:
    - 'save': Store a new lesson or technical insight. (e.g., topic='React error fix', content='Use useEffect...')
    - 'search': Find existing knowledge based on keywords in the topic.
    - 'list': Show all available knowledge topics.
    """
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["save", "search", "list"],
                "description": "The command to execute."
            },
            "topic": {
                "type": "string",
                "description": "The subject/title of the knowledge item."
            },
            "content": {
                "type": "string",
                "description": "The actual knowledge or solution to save."
            },
            "query": {
                "type": "string",
                "description": "Keyword to search for in topics."
            }
        },
        "required": ["command"]
    }

    base_dir: str = "knowledge"

    def _ensure_dir(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    async def execute(self, command: str, **kwargs) -> str:
        self._ensure_dir()
        
        if command == "save":
            topic = kwargs.get("topic")
            content = kwargs.get("content")
            if not topic or not content:
                return "Error: Both 'topic' and 'content' are required to save knowledge."
            
            # Sanitize filename
            filename = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
            file_path = os.path.join(self.base_dir, f"{filename}.json")
            
            data = {"topic": topic, "content": content}
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return f"Success: Knowledge saved under topic '{topic}' in {file_path}"

        elif command == "search":
            query = kwargs.get("query", "").lower()
            if not query:
                return "Error: 'query' is required for searching."
            
            results = []
            for filename in os.listdir(self.base_dir):
                if filename.endswith(".json"):
                    if query in filename.lower() or query in filename.replace('_', ' ').lower():
                        file_path = os.path.join(self.base_dir, filename)
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            results.append(f"Topic: {data.get('topic')}\nContent: {data.get('content')}")
            
            if not results:
                return f"No knowledge found matching '{query}'."
            
            return "\n---\n".join(results)

        elif command == "list":
            files = [f.replace(".json", "").replace("_", " ") for f in os.listdir(self.base_dir) if f.endswith(".json")]
            if not files:
                return "The knowledge base is currently empty."
            return "Available topics:\n- " + "\n- ".join(files)

        return f"Error: Unknown command '{command}'"
