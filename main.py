import asyncio
import sys
from loguru import logger
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel

from agent_core import ManusCompetition
from schema import Memory, Message, AgentState

# Configure logger to output to stdout nicely
logger.remove()
logger.add(RichHandler(rich_tracebacks=True, markup=True), format="{message}", level="INFO")

async def main():
    console = Console()
    console.print(Panel.fit(
        "[bold green]Manus-Cu-Sen ULTIMATE[/bold green]\n[dim](Brain Transplant Edition)[/dim]\n\nPowered by: [cyan]Browser-Use[/cyan], [magenta]Vision Context[/magenta], & [yellow]Dynamic Prompts[/yellow]",
        border_style="green",
        title="Welcome"
    ))

    # Initialize Memory
    memory = Memory()

    # Initialize Agent
    agent = ManusCompetition()
    agent.initialize(memory)

    print("\nReady! type 'exit' to quit.\n")

    try:
        while True:
            try:
                user_input = input("\nUser: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                
                # Re-initialize with user input for complexity detection
                agent.initialize(agent.memory, user_input)
                
                # Add user message to memory
                agent.memory.add_message(Message.user_message(user_input))
                
                print("\n" + "-"*30)
                # Run the agent (it logs its own thoughts/actions)
                await agent.run()
                
                # Check for final answer to display prominently
                if agent.final_answer:
                     console.print("\n" + "─"*50)
                     console.print(f"[bold green]Manus-Cu-Sen:[/bold green]\n{agent.final_answer}")
                     console.print("─"*50)
                
                print("\n" + "-"*30)
                
                # Reset for next turn (keep memory, reset counters)
                agent.current_step = 0
                agent.state = AgentState.IDLE
                agent.final_answer = None
                agent._is_complex_task = False  # Reset complexity flag
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Runtime Error: {e}")
                import traceback
                traceback.print_exc()
                
    finally:
        # Save usage stats before exiting
        if hasattr(agent, 'llm') and hasattr(agent.llm, 'save_usage'):
            agent.llm.save_usage()
            console.print(f"\n[dim]{agent.llm.get_usage_summary()}[/dim]")
        
        if agent.browser_context_helper:
            await agent.browser_context_helper.cleanup_browser()
        print("\nGoodbye!")

if __name__ == "__main__":
    asyncio.run(main())
