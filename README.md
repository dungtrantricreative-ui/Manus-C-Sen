# 🐉 Manus-Củ-Sen ULTIMATE (Core Edition)

> **The Supreme Autonomous AI Agent Engine**

**Manus-Củ-Sen ULTIMATE** is a high-performance, hardened AI engine designed for complex tasks, deep web research, and autonomous system management. Inspired by the OpenManus architecture, it operates on a rigid **Plan-First -> Execute -> Critic** loop, ensuring stability and accuracy in every step.

---

## 🚀 Key Features

### 🧠 Autonomous Intelligence
- **Plan-First Architecture**: For any non-trivial request, the agent creates a multi-step roadmap before taking action.
- **Critic Phase**: A self-correcting loop where the agent evaluates its own output and pivots if results are unsatisfactory.
- **Supreme Persistence**: Built to investigate and fix tool failures autonomously.

### 🛡️ Industrial-Grade Robustness (New)
- **Token Sanitization**: Multi-layered protection that strips internal LLM control tokens (e.g., `<|end_header_id|>`) to prevent `BadRequestError (400)`.
- **Surgical Truncation**: Advanced head/tail preservation for large data outputs, saving ~50% on token costs while keeping critical info.
- **Auto-Quoting Terminal**: Intelligent path detection that automatically wraps commands in quotes to prevent shell parsing errors on Windows.

### 🛠️ Professional Toolsuite
- **🌐 Vision Browser**: Index-based navigation with a vision-assisted model for perfect clicks and data extraction.
- **💻 Smart Terminal**: System-integrated command execution (Python/Pip) with automatic error recovery.
- **🔍 Search-to-Browser Failover**: If search results are poor, the critic automatically forces a deep browser research.
- **🎙️ Transcription**: Local-first audio processing for M4A, WAV, and MP3 files.

---

## 🏗️ Project Structure

- `agent_core.py`: The heart of the engine (Planning & Logic).
- `schema.py`: Hardened data structures and API payload sanitization.
- `main.py`: High-performance CLI entry point.
- `tools/`: Autonomous modular capabilities (Browser, Search, Terminal, FileOps).
- `config.toml`: Unified configuration for API keys and provider failovers.

---

## ⚙️ Getting Started

### 1. Requirements
Ensure you have Python 3.10+ installed.

### 2. Setup
Install dependencies directly to your system environment:
```powershell
pip install -r requirements.txt
```

### 3. Configuration
Rename `config.toml.example` (if available) to `config.toml` and add your API keys (OpenAI, Gemini, or OpenRouter).

### 4. Run
Launch the supreme interface:
```powershell
python main.py
```

---

## 🔒 Hardening & Security

This version is specifically designed to operate reliably on **Free-Tier/Limited-Quota** environments:
- **Payload Purity**: Strips all non-standard metadata from API calls.
- **Context Management**: Manual and automatic memory trimming to stay within context windows.
- **Prompt Discipline**: Strict system instructions to prevent "hallucination" and ensure task completion.

---

## 📜 License
MIT License. Optimized for the developer community.

*"Manus-Củ-Sen: Intelligence that doesn't just talk, it acts."*
