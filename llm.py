import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from schema import Message

class LLM:
    def __init__(self):
        # Primary Client
        self.primary_client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL
        )
        # Dynamic Backup Clients - only load those that support tools
        self.backup_clients = []
        for b in settings.BACKUPS:
            if b.api_key and b.supports_tools:  # Filter by tool support
                self.backup_clients.append({
                    "name": b.name,
                    "client": AsyncOpenAI(api_key=b.api_key, base_url=b.base_url),
                    "model": b.model_name
                })

        if self.backup_clients:
            logger.info(f"Loaded {len(self.backup_clients)} backup provider(s): {', '.join([b['name'] for b in self.backup_clients])}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def ask_tool_stream(self, messages: List[Any], tools: List[dict], model: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        # Pre-process messages
        msg_dicts = [m.to_dict() if hasattr(m, "to_dict") else m for m in messages]

        # Try primary first
        try:
            logger.debug(f"DEBUG LLM TOOLS: {json.dumps(tools, indent=2)}")
            response = await self.primary_client.chat.completions.create(
                model=model or settings.MODEL_NAME,
                messages=msg_dicts,
                tools=tools,
                tool_choice="auto",
                stream=True
            )
            async for chunk in response:
                yield chunk
            return # Success
        except Exception as e:
            if not self.backup_clients or not any(x in str(e).lower() for x in ["429", "rate limit", "timeout", "connection"]):
                raise e
            logger.debug(f"Primary LLM failed: {e}. Starting failover sequence...")

        # Try backups in order
        for b in self.backup_clients:
            try:
                logger.info(f"Failover: Switching to {b['name']} ({b['model']})")
                response = await b['client'].chat.completions.create(
                    model=b['model'],
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    stream=True
                )
                async for chunk in response:
                    yield chunk
                return
            except Exception as be:
                logger.warning(f"Backup {b['name']} failed: {be}")
        
        raise RuntimeError("All LLM providers failed.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def ask_tool(self, messages: List[Any], tools: List[dict], tool_choice: str = "auto", model: Optional[str] = None) -> Any:
        # Pre-process messages to ensure they are dicts
        msg_dicts = [m.to_dict() if hasattr(m, "to_dict") else m for m in messages]
        
        # Try primary first
        try:
            logger.debug(f"DEBUG LLM TOOLS: {json.dumps(tools, indent=2)}")
            return await self.primary_client.chat.completions.create(
                model=model or settings.MODEL_NAME,
                messages=msg_dicts,
                tools=tools,
                tool_choice=tool_choice,
                stream=False
            )
        except Exception as e:
             # Basic Failover logic for non-streaming
            if not self.backup_clients:
                raise e
            
            for b in self.backup_clients:
                try:
                    logger.info(f"Failover (Non-Stream): Switching to {b['name']}")
                    return await b['client'].chat.completions.create(
                        model=b['model'],
                        messages=messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        stream=False
                    )
                except Exception:
                    continue
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def quick_ask(self, messages: List[dict], model: Optional[str] = None) -> str:
        """Fast non-streaming response for simple queries (like Critic or vision decision)."""
        try:
            response = await self.primary_client.chat.completions.create(
                model=model or settings.MODEL_NAME,
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content or ""
        except Exception:
            # Fallback to first backup for robustness
            if self.backup_clients:
                 response = await self.backup_clients[0]['client'].chat.completions.create(
                    model=self.backup_clients[0]['model'],
                    messages=messages,
                    stream=False
                )
                 return response.choices[0].message.content or ""
            return ""
