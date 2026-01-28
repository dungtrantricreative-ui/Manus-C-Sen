import asyncio
import sys
from loguru import logger
from agent_core import AgentCore
from config import settings

async def main():
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set in .env file.")
        sys.exit(1)
        
    agent = AgentCore()
    
    print("\n--- Manus-Competition Initialized ---")
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
            
            result = await agent.run(user_input)
            print(f"\nManus: {result}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    asyncio.run(main())
