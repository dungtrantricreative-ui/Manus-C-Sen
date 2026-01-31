import asyncio
import sys
from loguru import logger

from agent_core import ManusCompetition
from schema import Memory, Message, AgentState

# Configure logger to output to stdout nicely
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>", level="DEBUG")

async def main():
    print("="*60)
    print("🐲 Manus-Củ-Sen ULTIMATE (Brain Transplant Edition)")
    print("   Powered by: Browser-Use, Vision Context, & Dynamic Prompts")
    print("="*60)

    # Initialize Memory
    memory = Memory()

    # Initialize Agent
    agent = ManusCompetition()
    agent.initialize(memory)

    print("\nReady! type 'exit' to quit.\n")

    try:
        while True:
            try:
                user_input = input("\n👤 User: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                
                # Add user message to memory
                agent.memory.add_message(Message.user_message(user_input))
                
                print("\n" + "-"*30)
                # Run the agent (it logs its own thoughts/actions)
                await agent.run()
                print("\n" + "-"*30)
                
                # Reset for next turn (keep memory, reset counters)
                agent.current_step = 0
                agent.state = AgentState.IDLE
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Runtime Error: {e}")
                import traceback
                traceback.print_exc()
                
    finally:
        if agent.browser_context_helper:
            await agent.browser_context_helper.cleanup_browser()
        print("\nGoodbye!")

if __name__ == "__main__":
    asyncio.run(main())
