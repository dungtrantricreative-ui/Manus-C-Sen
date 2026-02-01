import json
import os
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

# =============================================================================
# USAGE TRACKING & COST OPTIMIZATION
# =============================================================================

class UsageTracker:
    """Track token usage and costs across providers."""
    
    # Cost per million tokens (approximate, in USD)
    COST_PER_M_TOKENS = {
        "sambanova": {"input": 0.0, "output": 0.0},      # Free tier
        "sambanova_alt": {"input": 0.0, "output": 0.0},  # Free tier
        "groq": {"input": 0.05, "output": 0.10},         # Very cheap
        "cerebras": {"input": 0.10, "output": 0.10},     # Cheap
        "default": {"input": 1.0, "output": 2.0}         # Conservative estimate
    }
    
    def __init__(self, usage_file: str = "outputs/usage_stats.json"):
        self.usage_file = usage_file
        self.session_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_requests": 0,
            "estimated_cost_usd": 0.0,
            "by_provider": {},
            "session_start": datetime.now().isoformat()
        }
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
    
    def record_usage(self, provider: str, input_tokens: int, output_tokens: int):
        """Record token usage for a request."""
        self.session_stats["total_input_tokens"] += input_tokens
        self.session_stats["total_output_tokens"] += output_tokens
        self.session_stats["total_requests"] += 1
        
        # Calculate cost
        costs = self.COST_PER_M_TOKENS.get(provider, self.COST_PER_M_TOKENS["default"])
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
        self.session_stats["estimated_cost_usd"] += cost
        
        # Track by provider
        if provider not in self.session_stats["by_provider"]:
            self.session_stats["by_provider"][provider] = {
                "input_tokens": 0, "output_tokens": 0, "requests": 0, "cost_usd": 0.0
            }
        prov_stats = self.session_stats["by_provider"][provider]
        prov_stats["input_tokens"] += input_tokens
        prov_stats["output_tokens"] += output_tokens
        prov_stats["requests"] += 1
        prov_stats["cost_usd"] += cost
    
    def save(self):
        """Save usage statistics to file."""
        try:
            # Load existing stats if available
            existing = {}
            if os.path.exists(self.usage_file):
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            
            # Append this session
            if "sessions" not in existing:
                existing["sessions"] = []
            existing["sessions"].append(self.session_stats)
            
            # Update cumulative totals
            existing["cumulative"] = {
                "total_input_tokens": sum(s["total_input_tokens"] for s in existing["sessions"]),
                "total_output_tokens": sum(s["total_output_tokens"] for s in existing["sessions"]),
                "total_requests": sum(s["total_requests"] for s in existing["sessions"]),
                "total_cost_usd": sum(s["estimated_cost_usd"] for s in existing["sessions"])
            }
            
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save usage stats: {e}")
    
    def get_summary(self) -> str:
        """Get a summary of this session's usage."""
        s = self.session_stats
        return (
            f"📊 Session Stats: {s['total_requests']} requests, "
            f"{s['total_input_tokens'] + s['total_output_tokens']} tokens, "
            f"≈${s['estimated_cost_usd']:.4f}"
        )

# =============================================================================
# RESPONSE CACHE FOR COST SAVINGS
# =============================================================================

class ResponseCache:
    """Simple in-memory cache for repeated queries."""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, messages: List[dict], tools: List[dict] = None) -> str:
        """Create a cache key from messages and tools."""
        # Use last 3 messages for key (balance between precision and reuse)
        recent = messages[-3:] if len(messages) > 3 else messages
        key_parts = [str(m.get("content", ""))[:100] for m in recent]
        if tools:
            key_parts.append(str(len(tools)))  # Just tool count for key
        return hash(tuple(key_parts))
    
    def get(self, messages: List[dict], tools: List[dict] = None) -> Optional[Any]:
        """Get cached response if available."""
        key = self._make_key(messages, tools)
        if key in self.cache:
            self.hits += 1
            logger.debug(f"Cache hit! ({self.hits} hits, {self.misses} misses)")
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, messages: List[dict], response: Any, tools: List[dict] = None):
        """Cache a response."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        key = self._make_key(messages, tools)
        self.cache[key] = response

# =============================================================================
# MAIN LLM CLASS
# =============================================================================

class LLM:
    _instances_count = 0

    def __init__(self):
        # Primary Client
        self.primary_client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL
        )
        self.primary_name = "primary"
        
        # Dynamic Backup Clients - sorted by cost (cheapest first)
        raw_backups = []
        for b in settings.BACKUPS:
            if b.api_key and b.supports_tools:
                # Calculate cost score for sorting
                provider_key = b.name.split('_')[0].lower() # e.g. "groq_primary" -> "groq"
                costs = UsageTracker.COST_PER_M_TOKENS.get(provider_key, UsageTracker.COST_PER_M_TOKENS["default"])
                cost_score = costs["input"] + costs["output"]
                
                raw_backups.append({
                    "name": b.name,
                    "client": AsyncOpenAI(api_key=b.api_key, base_url=b.base_url),
                    "model": b.model_name,
                    "cost_score": cost_score
                })
        
        # PHASE 12: Sort backups by cost score (ASC)
        self.backup_clients = sorted(raw_backups, key=lambda x: x["cost_score"])
        
        # Usage tracking and caching
        self.usage_tracker = UsageTracker()
        self.cache = ResponseCache()

        if self.backup_clients and LLM._instances_count < 1:
            logger.success(f"⚡ FUSION: {len(self.backup_clients)} backup networks available.")
        
        LLM._instances_count += 1

    def _extract_usage(self, response, provider: str):
        """Extract and record token usage from response."""
        try:
            if hasattr(response, 'usage') and response.usage:
                self.usage_tracker.record_usage(
                    provider=provider,
                    input_tokens=response.usage.prompt_tokens or 0,
                    output_tokens=response.usage.completion_tokens or 0
                )
        except Exception:
            pass  # Usage tracking is best-effort

    def _prepare_messages(self, messages: List[Any], model: str) -> List[Dict[str, Any]]:
        """Pre-process messages for OpenAI compatibility, handling vision content."""
        msg_dicts = []
        supports_vision = any(x in model.lower() for x in ["vision", "vl", "gpt-4o", "claude-3", "gemini"])
        
        for m in messages:
            if hasattr(m, "to_dict"):
                d = m.to_dict()
            else:
                d = m.copy() if isinstance(m, dict) else dict(m)

            base64_img = d.pop("base64_image", None)
            
            if base64_img and supports_vision:
                original_content = d.get("content", "")
                d["content"] = [
                    {"type": "text", "text": original_content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                    }
                ]
            msg_dicts.append(d)
        return msg_dicts

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def ask_tool_stream(self, messages: List[Any], tools: List[dict], model: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        target_model = model or settings.MODEL_NAME
        msg_dicts = self._prepare_messages(messages, target_model)

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
            return
        except Exception as e:
            if not self.backup_clients or not any(x in str(e).lower() for x in ["429", "rate limit", "timeout", "connection"]):
                raise e
            logger.debug(f"Primary LLM failed: {e}. Starting failover sequence...")

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

    async def ask_tool(self, messages: List[Any], tools: List[dict], tool_choice: str = "auto", model: Optional[str] = None) -> Any:
        target_model = model or settings.MODEL_NAME
        msg_dicts = self._prepare_messages(messages, target_model)
        
        # PHASE 12: Optimized Caching
        if settings.cache.enabled:
            cached = self.cache.get(msg_dicts, tools)
            if cached:
                logger.success("🚀 Performance: Response served from cache.")
                return cached
        
        try:
            response = await self.primary_client.chat.completions.create(
                model=target_model,
                messages=msg_dicts,
                tools=tools,
                tool_choice=tool_choice,
                stream=False
            )
            self._extract_usage(response, self.primary_name)
            
            if settings.cache.enabled:
                self.cache.set(msg_dicts, response, tools)
            return response
        except Exception as e:
            # Clean up rate limit messages
            err_msg = str(e)
            if "Rate limit" in err_msg:
                err_msg = "Rate limit reached (Summarized)"
            logger.debug(f"Primary failed: {err_msg}")
            if not self.backup_clients:
                raise e
            
            # PHASE 12: Cost-Aware Failover (Clients are already added in sequence)
            for b in self.backup_clients:
                try:
                    logger.success(f"🔄 Failover: Switching to {b['name']}...")
                    msg_dicts_backup = self._prepare_messages(messages, b['model'])
                    response = await b['client'].chat.completions.create(
                        model=b['model'],
                        messages=msg_dicts_backup,
                        tools=tools,
                        tool_choice=tool_choice,
                        stream=False
                    )
                    self._extract_usage(response, b['name'])
                    return response
                except Exception as be:
                    logger.debug(f"Backup provider {b['name']} also failed: {be}")
                    continue
            raise e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=15))
    async def quick_ask(self, messages: List[dict], model: Optional[str] = None) -> str:
        """Fast non-streaming response for simple queries (summarization, etc.)."""
        target_model = model or settings.MODEL_NAME
        try:
            response = await self.primary_client.chat.completions.create(
                model=target_model,
                messages=messages,
                stream=False
            )
            self._extract_usage(response, self.primary_name)
            return response.choices[0].message.content or ""
        except Exception:
            if self.backup_clients:
                response = await self.backup_clients[0]['client'].chat.completions.create(
                    model=self.backup_clients[0]['model'],
                    messages=messages,
                    stream=False
                )
                self._extract_usage(response, self.backup_clients[0]['name'])
                return response.choices[0].message.content or ""
            return ""
    
    def get_usage_summary(self) -> str:
        """Get current session usage summary."""
        return self.usage_tracker.get_summary()
    
    def save_usage(self):
        """Save usage stats to file."""
        self.usage_tracker.save()
