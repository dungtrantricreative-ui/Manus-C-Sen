import json
import os
from datetime import datetime
from loguru import logger
from config import settings

class Monitoring:
    @staticmethod
    def track_request(prompt_tokens: int = 0, completion_tokens: int = 0):
        if not settings.TRACK_USAGE:
            return

        usage_file = settings.USAGE_FILE
        today = datetime.now().strftime("%Y-%m-%d")
        
        data = {}
        if os.path.exists(usage_file):
            try:
                with open(usage_file, "r") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load usage file: {e}")

        if today not in data:
            data[today] = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "estimated_cost": 0.0}

        data[today]["requests"] += 1
        data[today]["prompt_tokens"] += prompt_tokens
        data[today]["completion_tokens"] += completion_tokens
        
        # Rough cost estimation (Llama 4 values or generic)
        # Assuming $0.05 per 1M tokens for prompt and $0.10 for completion
        cost = (prompt_tokens * 0.05 / 1000000) + (completion_tokens * 0.10 / 1000000)
        data[today]["estimated_cost"] += cost

        try:
            with open(usage_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save usage file: {e}")

    @staticmethod
    def log_cache_stats(hit: bool):
        if hit:
            logger.debug("⚡ Cache Hit!")
        else:
            logger.debug("❄️ Cache Miss.")
