import os
import sys
import logging
from loguru import logger

# 1. SILENCE NOISY LOGS IMMEDIATELY (Before any other imports)
logger.remove()
from rich.logging import RichHandler
logger.add(RichHandler(rich_tracebacks=True, markup=True), format="[dim]{time:HH:mm:ss}[/dim] {message}", level="SUCCESS")

# Set levels for standard logging
logging.getLogger("browser_use").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("openai").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)

# Prevent browser_use from configuring its own logging if it hasn't already
os.environ["BROWSER_USE_LOGGING_LEVEL"] = "CRITICAL"

import asyncio
from rich.console import Console
from rich.panel import Panel

from agent_core import ManusCompetition
from schema import Memory, Message, AgentState

async def main():
    console = Console()
    console.print(Panel.fit(
        "[bold green]Manus-Cu-Sen ULTIMATE[/bold green]\n[dim](Brain Transplant Edition)[/dim]\n\nPowered by: [cyan]Browser-Use[/cyan], [magenta]Vision Context[/magenta], & [yellow]Dynamic Prompts[/yellow]",
        border_style="green",
        title="Welcome"
    ))

    # Initialize Memory
    memory = Memory()

    # Initialize Agent (Now handles its own Memory and System Prompt internally)
    agent = ManusCompetition()
    
    print("\nReady! type 'exit' to quit.\n")

    try:
        while True:
            try:
                user_input = input("\nUser: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                
                # Initialize complexity and user message
                agent.initialize(user_input)
                
                print("\n" + "-"*30)
                # Run the agent
                await agent.run()
                
                # Check for final answer
                if agent.final_answer:
                     console.print("\n" + "─"*50)
                     console.print(f"[bold green]Manus-Cu-Sen:[/bold green]\n{agent.final_answer}")
                     console.print("─"*50)
                
                print("\n" + "-"*30)
                
                # Reset for next turn
                agent.current_step = 0
                agent.state = AgentState.IDLE
                agent.final_answer = None
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Runtime Error: {e}")
                
    finally:
        # Save usage stats
        if hasattr(agent, 'llm') and hasattr(agent.llm, 'save_usage'):
            agent.llm.save_usage()
            console.print(f"\n[dim]{agent.llm.get_usage_summary()}[/dim]")
        
        # Cleanup any active tools (like browser)
        if hasattr(agent.available_tools, "get_tool"):
            browser_tool = agent.available_tools.get_tool("browser_use")
            if browser_tool and hasattr(browser_tool, "cleanup"):
                await browser_tool.cleanup()
        
        print("\nGoodbye!")

if __name__ == "__main__":
    asyncio.run(main())
