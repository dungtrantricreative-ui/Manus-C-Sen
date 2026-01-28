import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from loguru import logger
from config import settings
from tools.search import search_tool

SYSTEM_PROMPT = """You are Manus-Competition, an ultra-optimized AI agent. 
Goal: Solve tasks efficiently with minimum tokens.
Rules:
1. THINK: Brief reasoning for the next step.
2. ACT: Call tools to get information or perform actions.
3. OBSERVE: Process tool output.
4. FINISH: Provide final answer when done.

Tool:
- search_tool(query: str): Search web for info.

Format:
Use the provided tool calling interface. Be direct. No conversational filler."""

class AgentCore:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.BASE_URL
        )
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_tool",
                    "description": "Search the web for real-time information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        self.available_tools = {
            "search_tool": search_tool
        }

    async def run(self, user_input: str):
        self.messages.append({"role": "user", "content": user_input})
        
        for step in range(settings.MAX_STEPS):
            logger.info(f"Step {step + 1}/{settings.MAX_STEPS}")
            
            response = await self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            self.messages.append(message)
            
            if message.content:
                logger.info(f"Thought: {message.content}")
            
            if not message.tool_calls:
                return message.content
            
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if name in self.available_tools:
                    result = self.available_tools[name](**args)
                    logger.info(f"Action: {name} completed.")
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": result
                    })
                else:
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": f"Error: Tool {name} not found."
                    })
        
        return "Final result: Reached maximum steps without completion."
