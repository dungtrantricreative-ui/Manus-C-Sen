import os
import toml
from pydantic import BaseModel, Field
from typing import List

class BackupProvider(BaseModel):
    name: str = "backup"
    api_key: str = ""
    model_name: str = ""
    base_url: str = ""
    supports_tools: bool = True  # Default to True for backward compatibility

class LLMSettings(BaseModel):
    api_key: str = ""
    model_name: str = "gpt-oss-120b"
    vision_model_name: str = "llama-4-maverick-17b-128e-instruct"
    base_url: str = "https://api.sambanova.ai/v1"
    
    # List of additional backup providers
    backups: List[BackupProvider] = []

class ToolSettings(BaseModel):
    tavily_api_key: str = ""
    enabled: List[str] = ["search", "memory", "file_ops", "calculator", "scraper"]

class AgentSettings(BaseModel):
    max_steps: int = 20
    name: str = "Manus-Củ-Sen"

class CacheSettings(BaseModel):
    enabled: bool = True
    ttl_seconds: int = 300

class MemoryStoreSettings(BaseModel):
    file_path: str = "memory.json"
    max_age_days: int = 7

class MonitoringSettings(BaseModel):
    track_usage: bool = True
    usage_file: str = "usage.json"

class Settings(BaseModel):
    llm: LLMSettings = LLMSettings()
    tools: ToolSettings = ToolSettings()
    agent: AgentSettings = AgentSettings()
    cache: CacheSettings = CacheSettings()
    memory: MemoryStoreSettings = MemoryStoreSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    @classmethod
    def load(cls):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.toml")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_temp = toml.load(f)
        else:
            config_temp = {}

        return cls(**config_temp)

settings_obj = Settings.load()

# For backward compatibility and easy access
class LegacySettings:
    def __init__(self, s: Settings):
        self.API_KEY = s.llm.api_key
        self.MODEL_NAME = s.llm.model_name
        self.VISION_MODEL_NAME = s.llm.vision_model_name
        self.BASE_URL = s.llm.base_url
        
        # Multiple Backup Providers
        self.BACKUPS = s.llm.backups
        
        self.TAVILY_API_KEY = s.tools.tavily_api_key
        self.MAX_STEPS = s.agent.max_steps
        
        # New settings access
        self.ENABLED_TOOLS = s.tools.enabled
        self.CACHE_ENABLED = s.cache.enabled
        self.CACHE_TTL = s.cache.ttl_seconds
        self.MEMORY_FILE = s.memory.file_path
        self.TRACK_USAGE = s.monitoring.track_usage
        self.USAGE_FILE = s.monitoring.usage_file
        self.name = s.agent.name

settings = LegacySettings(settings_obj)
