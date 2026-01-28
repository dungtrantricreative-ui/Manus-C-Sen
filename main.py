import asyncio
import sys
from loguru import logger
from agent_core import ManusCompetition
from tools.search import SearchTool
from config import settings

async def main():
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set.")
        return
        
    # Initialize the agent with robust original logic
    agent = ManusCompetition()
    agent.add_tool(SearchTool())
    
    print("\n🚀 Manus-Competition (Robust Edition) Initialized")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
            
            # Reset agent state for new query if needed, or keep context
            # Original Manus usually creates a new instance or clears memory
            # For competition, we let it keep context in a session
            result = await agent.run(user_input)
            print(f"\nManus: {result}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, format="<blue>{time:HH:mm:ss}</blue> | <level>{level}</level> | {message}")
    asyncio.run(main())
