import asyncio
import sys
from loguru import logger
from agent_core import ManusCompetition
from tools.search import SearchTool
from tools.file_ops import FileOpsTool
from tools.memory import MemoryTool
from tools.calculator import CalculatorTool
from tools.scraper import ScraperTool
from tools.python_repl import PythonREPLTool
from tools.browser import BrowserTool
from tools.ask_human import AskHumanTool
from tools.terminal import TerminalTool
from config import settings

async def main():
    if not settings.API_KEY:
        logger.error("api_key is not set in config.toml.")
        return
        
    agent = ManusCompetition()
    
    # Registry tools based on config
    tool_map = {
        "search": SearchTool(),
        "file_ops": FileOpsTool(),
        "memory": MemoryTool(),
        "calculator": CalculatorTool(),
        "scraper": ScraperTool(),
        "python_repl": PythonREPLTool(),
        "browser": BrowserTool(),
        "ask_human": AskHumanTool(),
        "terminal": TerminalTool()
    }
    
    for tool_name in settings.ENABLED_TOOLS:
        if tool_name in tool_map:
            agent.add_tool(tool_map[tool_name])
            logger.info(f"Tool enabled: {tool_name}")
    
    print(f"\n🚀 {settings.name} Advanced Initialized")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
            
            # Start the logic
            async for chunk in agent.run(user_input):
                if chunk["type"] == "status":
                    # Print status on its own line with a subtle color
                    print(f"\n\033[93m>> {chunk['content']}\033[0m")
                    print(f"\033[34m{settings.name}:\033[0m ", end="", flush=True)
                elif chunk["type"] == "content":
                    print(chunk["content"], end="", flush=True)
            
            print("\n") # End of response
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            # Cleanup all tools that have a cleanup method
            for tool in tool_map.values():
                if hasattr(tool, "cleanup") and asyncio.iscoroutinefunction(tool.cleanup):
                    await tool.cleanup()

if __name__ == "__main__":
    logger.remove()
    # Set to INFO level to avoid confusing the user with DEBUG cache logs
    logger.add(sys.stderr, level="INFO", format="<blue>{time:HH:mm:ss}</blue> | <level>{level}</level> | {message}")
    asyncio.run(main())
