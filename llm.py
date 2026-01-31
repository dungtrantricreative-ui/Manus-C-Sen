import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from schema import Message

class LLM:
    _instances_count = 0

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

        # Reduce logging noise: only log backups if we haven't logged many times already
        if self.backup_clients and LLM._instances_count < 1:
            logger.info(f"Loaded {len(self.backup_clients)} backup provider(s): {', '.join([b['name'] for b in self.backup_clients])}")
        
        LLM._instances_count += 1

    def _prepare_messages(self, messages: List[Any], model: str) -> List[Dict[str, Any]]:
        """Pre-process messages for OpenAI compatibility, handling vision content."""
        msg_dicts = []
        # Basic vision support check: very simple heuristic for now
        # Most "vision" models have 'vision', 'vl', or 'scout' in name? 
        # Actually, let's just format anyway if base64 is present, but some models crash.
        # Hardening: Only include vision if model name suggests vision OR if it's explicitly allowed.
        supports_vision = any(x in model.lower() for x in ["vision", "vl", "gpt-4o", "claude-3", "gemini"])
        
        for m in messages:
            if hasattr(m, "to_dict"):
                d = m.to_dict()
            else:
                d = m.copy() if isinstance(m, dict) else dict(m)

            # Extract base64_image if present (added by schema.py Message.to_dict)
            base64_img = d.pop("base64_image", None)
            
            if base64_img and supports_vision:
                # Format into standard OpenAI content list
                original_content = d.get("content", "")
                d["content"] = [
                    {"type": "text", "text": original_content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                    }
                ]
            # If model doesn't support vision, just keep the text content (already in 'content' field)
            msg_dicts.append(d)
        return msg_dicts

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def ask_tool_stream(self, messages: List[Any], tools: List[dict], model: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        target_model = model or settings.MODEL_NAME
        msg_dicts = self._prepare_messages(messages, target_model)

        # Try primary first
        try:
            response = await self.primary_client.chat.completions.create(
                model=target_model,
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
                msg_dicts_backup = self._prepare_messages(messages, b['model'])
                response = await b['client'].chat.completions.create(
                    model=b['model'],
                    messages=msg_dicts_backup,
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
        target_model = model or settings.MODEL_NAME
        msg_dicts = self._prepare_messages(messages, target_model)
        
        # Try primary first
        try:
            return await self.primary_client.chat.completions.create(
                model=target_model,
                messages=msg_dicts,
                tools=tools,
                tool_choice=tool_choice,
                stream=False
            )
        except Exception as e:
            if not self.backup_clients:
                raise e
            
            for b in self.backup_clients:
                try:
                    logger.info(f"Failover (Non-Stream): Switching to {b['name']}")
                    msg_dicts_backup = self._prepare_messages(messages, b['model'])
                    return await b['client'].chat.completions.create(
                        model=b['model'],
                        messages=msg_dicts_backup,
                        tools=tools,
                        tool_choice=tool_choice,
                        stream=False
                    )
                except Exception:
                    continue
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def quick_ask(self, messages: List[dict], model: Optional[str] = None) -> str:
        """Fast non-streaming response for simple queries."""
        target_model = model or settings.MODEL_NAME
        try:
            response = await self.primary_client.chat.completions.create(
                model=target_model,
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content or ""
        except Exception:
            if self.backup_clients:
                 response = await self.backup_clients[0]['client'].chat.completions.create(
                    model=self.backup_clients[0]['model'],
                    messages=messages,
                    stream=False
                )
                 return response.choices[0].message.content or ""
            return ""
