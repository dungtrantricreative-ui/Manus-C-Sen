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
*   **Maverick Vision Specialist**: Uses the specialized **Llama-4-Maverick** model to analyze screenshots and interact with web elements with human-like precision.
*   **Cost Optimized**: Intelligent DOM simplification reduces token usage by up to 70% without losing context.

### 🛡️ Multi-Provider Failover System
*   **SambaNova Primary**: leverages high-parameter models like **GPT-OSS-120B** for deep reasoning.
*   **Groq Backup**: Automatically fails over to **Groq (Llama 4 Scout)** if the primary provider hits a 429 Rate Limit or experiences downtime.

### 🤝 Human-in-the-loop (`ask_human`)
*   When blocked by ambiguity or requiring permission for sensitive actions (e.g., payments, deletion), the AI will pause and ask you for guidance directly in the console.

### 🐍 Integrated Python Sandbox
*   Includes a Python REPL for complex math, data analysis, and chart generation on the fly.

---

## 🏁 Quick Start Guide

### 1. Prerequisites
*   Python 3.10+
*   API Keys: SambaNova Cloud (Primary) and/or Groq (Backup).

### 2. Installation

```powershell
# Clone the repository
git clone https://github.com/your-repo/manus-cu-sen.git
cd manus-cu-sen

# Install dependencies
pip install -r requirements.txt

# Install Playwright Browser binaries (Crucial for BrowserTool)
python -m playwright install chromium
```

### 3. Configuration
Edit `config.toml` in the project root:

```toml
[llm]
gemini_api_key = "YOUR_SAMBANOVA_KEY"
model_name = "gpt-oss-120b"
vision_model_name = "llama-4-maverick-17b-128e-instruct"
base_url = "https://api.sambanova.ai/v1"

# GROQ BACKUP (Highly Recommended)
groq_api_key = "YOUR_GROQ_KEY"
groq_model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
groq_base_url = "https://api.groq.com/openai/v1"
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
