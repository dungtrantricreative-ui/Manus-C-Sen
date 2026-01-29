import os
import toml
from pydantic import BaseModel

class LLMSettings(BaseModel):
    gemini_api_key: str = ""
    model_name: str = "gemini-2.0-flash-exp"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

class ToolSettings(BaseModel):
    tavily_api_key: str = ""

class AgentSettings(BaseModel):
    max_steps: int = 20
    name: str = "Manus-Củ-Sen"

class Settings(BaseModel):
    llm: LLMSettings = LLMSettings()
    tools: ToolSettings = ToolSettings()
    agent: AgentSettings = AgentSettings()

    @classmethod
    def load(cls):
        config_path = "config.toml"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = toml.load(f)
        else:
            config_data = {}

        return cls(**config_data)

settings_obj = Settings.load()

# For backward compatibility with existing code
class LegacySettings:
    def __init__(self, s: Settings):
        self.GEMINI_API_KEY = s.llm.gemini_api_key
        self.MODEL_NAME = s.llm.model_name
        self.BASE_URL = s.llm.base_url
        self.TAVILY_API_KEY = s.tools.tavily_api_key
        self.MAX_STEPS = s.agent.max_steps

settings = LegacySettings(settings_obj)
