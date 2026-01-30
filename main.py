import asyncio
import sys
from loguru import logger
from agent_core import ManusCompetition
from tools.browser import BrowserTool
from tools.search import SearchTool
from tools.terminal import TerminalTool
from tools.file_ops import FileOpsTool
from tools.transcription import TranscriptionTool
from tools.planning import PlanningTool
from event_bus import EventBus

# Custom bridge to print events to terminal instead of WebSocket
async def terminal_event_bridge(event: dict):
    event_type = event.get("type")
    content = event.get("content", "")
    
    if event_type == "thinking":
        print(f"\n[THINKING] {content}")
    elif event_type == "terminal":
        print(f"\n[TERMINAL OUTPUT]\n{content}")
    elif event_type == "status":
        print(f"\n[STATUS] {content}")
    elif event_type == "content":
        print(f"\n{content}")
    elif event_type == "browser_view":
        # In CLI, we just notify that a screenshot was taken
        print(f"\n[BROWSER] Screenshot captured.")

async def main():
    # Setup EventBus for CLI
    EventBus.subscribe(terminal_event_bridge)
    
    print("="*50)
    print("Manus-Củ-Sen CLI Edition (No GUI)")
    print("="*50)
    
    agent = ManusCompetition()
    
    # Initialize tools
    browser_tool = BrowserTool()
    agent.add_tool(SearchTool())
    agent.add_tool(TerminalTool())
    agent.add_tool(FileOpsTool())
    agent.add_tool(TranscriptionTool())
    agent.add_tool(PlanningTool())
    agent.add_tool(browser_tool)
    
    try:
        while True:
            try:
                user_input = input("\n👤 User: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                
                print("\n" + "-"*30)
                async for chunk in agent.run(user_input):
                    if chunk.get("type") == "content":
                        print(chunk.get("content", ""), end="", flush=True)
                print("\n" + "-"*30)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                
    finally:
        await browser_tool.cleanup()
        print("\nGoodbye!")

if __name__ == "__main__":
    asyncio.run(main())
