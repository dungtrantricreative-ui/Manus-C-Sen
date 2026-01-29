# 🏆 Manus-Competition

**Ultra-streamlined, ReAct-based AI agent optimized for Gemini 2.x Flash.**

## 🚀 1-Click Install

### Windows
```powershell
python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt
```

### Linux/macOS
```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

## ⚙️ Configuration
Edit the `config.toml` file in the root directory:
```toml
[llm]
gemini_api_key = "your_key"
model_name = "meta-llama/llama-4-scout-17b-16e-instruct"
base_url = "https://api.groq.com/openai/v1"

[tools]
enabled = ["search", "memory", "file_ops", "calculator", "scraper"]

[cache]
enabled = true
```

## 🛠️ Advanced Tools
- **File Operations**: Read/Write/List files in your workspace.
- **Persistent Memory**: Save and recall info across sessions (stored in `memory.json`).
- **Calculator**: Securely solve mathematical expressions.
- **Web Scraper**: Extract full text content from any URL.

## 🚀 Key Features
- **Streaming UI**: See response chunks and agent status real-time.
- **Intelligent Caching**: Avoid redundant tool calls for the same query.
- **Self-Correction**: RL-inspired reflection loop for high accuracy.
- **Usage Monitoring**: Track request counts and estimated costs in `usage.json`.

## 🎯 Run
```bash
python main.py
```

## 🛠️ Project Structure
- `main.py`: Entry point.
- `agent_core.py`: Lightweight ReAct loop & optimized Gemini prompts.
- `config.py`: Configuration management.
- `tools/`: Modular tools (Search included).

## ⚡ Key Optimizations
- **Browserless**: No Playwright/Chromium dependencies.
- **Fast**: Instruction-based prompts for Gemini 2.0 Flash.
- **Pure ReAct**: Minimal overhead logic.
