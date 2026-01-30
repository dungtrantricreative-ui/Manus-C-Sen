# Manus-Củ-Sen Core Edition

This is the pure AI engine of the Manus-Củ-Sen project, stripped of all GUI, Web Server, and Static assets. It is designed for developers who want to integrate the core agentic logic into other applications or use it via terminal.

## Contents
- `agent_core.py`: The main Planning-Execution-Critic loop.
- `main.py`: CLI entry point for terminal interaction.
- `tools/`: Full suite of tools (Browser, Terminal, Search, FileOps).
- `config.toml`: Agent credentials and failover settings.

## How to use
1. Ensure dependencies are installed: `pip install -r requirements.txt`
2. Run directly in terminal: `python main.py`

This version is optimized for backend usage and raw performance.
