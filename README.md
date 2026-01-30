# 🏆 Manus-Củ-Sen: The Autonomous Multi-Agent Orchestrator

**Manus-Củ-Sen** is a next-generation, high-performance AI Agent founded on the principles of the original Manus project but optimized for extreme cost-efficiency and modularity. It transforms a standard LLM into an autonomous agent capable of browsing the web, executing code, and self-correcting through its unique **Planner-Executor-Critic** engine.

---

## 🚀 The "Củ Sen" Engine (Architecture)

Manus-Củ-Sen doesn't just "chat"—it thinks and acts through a three-stage specialized loop:

1.  **🧠 Manager (The Planner)**: Analyzes user intent and breaks down complex requests into a step-by-step logical roadmap.
2.  **🛠️ Executor (The Specialist)**: Utilizes a suite of tools (Browser with Vision, Python REPL, Search) to perform actions.
3.  **⚖️ Critic (The Verifier)**: A high-level reflection agent that automatically reviews the Executor's output. If the result is insufficient, it sends feedback to the Manager to adjust the strategy.

---

## ✨ Key Features

### 👁️ Dual-Model Visible Browser
*   **Visible Interaction**: Watch the AI work in real-time as a browser window opens on your desktop.
*   **Maverick Vision Specialist**: Uses specialized Vision models to analyze screenshots and interact with web elements.

### 💻 Terminal/Shell Empowerment
*   **CMD & PowerShell Access**: The AI can now execute terminal commands to manage files, install dependencies, or run scripts directly on your system.

### 🛡️ Infinite Failover System
*   **Dynamic Backups**: Add unlimited backup providers in `config.toml`. The agent will automatically cycle through them if the primary provider hits a rate limit (429) or connection error.

---

## 🏁 Quick Start Guide

### 1. Prerequisites
*   Python 3.10+
*   API Keys: SambaNova (Primary), Groq, or OpenRouter (Backups).

### 2. Installation
```powershell
# Clone and install
git clone https://github.com/your-repo/manus-cu-sen.git
cd manus-cu-sen
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Configuration
Edit `config.toml` in the project root. We use a standardized **`api_key`** format for all providers:

```toml
[llm]
api_key = "PRIMARY_KEY_HERE"
model_name = "gpt-oss-120b"
base_url = "https://api.sambanova.ai/v1"

# --- Add as many backups as you want ---
[[llm.backups]]
name = "groq_backup"
api_key = "GROQ_KEY_HERE"
model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
base_url = "https://api.groq.com/openai/v1"

[[llm.backups]]
name = "openrouter_backup"
api_key = "OR_KEY_HERE"
model_name = "deepseek/deepseek-chat"
base_url = "https://openrouter.ai/api/v1"
```

### 4. Run the Agent
```bash
python main.py
```

---

## 🛠️ Project Structure

*   `main.py`: The entry point and tool registry.
*   `agent_core.py`: The heart of the Planner-Executor-Critic loop.
*   `tools/`: Modular capability system:
    *   `browser.py`: Playwright integration with Maverick Vision.
    *   `ask_human.py`: Interactive human feedback loop.
    *   `python_repl.py`: Sandboxed code execution.
    *   `file_ops.py`: File system management (reports, docs).
    *   `memory.py`: Persistent context storage.

---

## 🤝 Contributing
Contributions are what make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch
3. Commit your Changes
4. Push to the Branch
5. Open a Pull Request

---

*Built with passion for the AI community. Optimized for real-world performance.*
