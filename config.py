import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = "gemini-2.0-flash-exp"
    BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # Tool Settings
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Agent Settings
    MAX_STEPS: int = 20
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
