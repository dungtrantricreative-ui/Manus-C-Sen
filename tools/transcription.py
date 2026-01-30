from base_tool import BaseTool
import os
from openai import AsyncOpenAI
from config import settings
from loguru import logger

class TranscriptionTool(BaseTool):
    name: str = "transcribe"
    description: str = """Transcribe an audio file (mp3, mp4, mpeg, mpga, m4a, wav, or webm) into text. 
    Use this to understand the content of audio files provided by the user."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the audio file."
            }
        },
        "required": ["file_path"]
    }

    async def execute(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        
        try:
            # Use a fresh client for transcription to ensure correct base_url/model
            # Most providers use the standard OpenAI whisper-1 model name
            client = AsyncOpenAI(api_key=settings.API_KEY, base_url=settings.BASE_URL)
            
            with open(file_path, "rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            
            return f"Transcription of {os.path.basename(file_path)}:\n\n{transcription.text}"
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error transcribing file: {str(e)}"
