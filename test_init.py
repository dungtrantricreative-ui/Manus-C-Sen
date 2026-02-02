import asyncio
from agent_core import ManusPrime
from loguru import logger
import sys

# Increase log level for debugging
logger.remove()
logger.add(sys.stderr, level="DEBUG")

async def test():
    print("Initializing ManusPrime...")
    try:
        agent = ManusPrime()
        print("ManusPrime initialized successfully!")
        print(f"Name: {agent.name}")
        print(f"System Prompt length: {len(agent.system_prompt)}")
    except Exception as e:
        print(f"Error during initialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
