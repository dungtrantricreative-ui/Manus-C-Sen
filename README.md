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
gemini_api_key = "your_gemini_api_key"
model_name = "gemini-2.0-flash-exp"

[tools]
tavily_api_key = "your_tavily_api_key"
```

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
