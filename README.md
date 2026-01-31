# 🐉 Manus-Củ-Sen ULTIMATE (Brain Transplant Edition)

> **The Supreme Autonomous AI Agent Engine: Powered by OpenManus Logic, Vision Browsing, & Dynamic Context.**

**Manus-Củ-Sen ULTIMATE** has completed a major "Brain Transplant" (Phase 11). It now runs on the core logic of the OpenManus project, enhanced with strict environment hardening. It features a vision-powered browser, dynamic "context-aware" prompting, and robust tool execution.

---

## 📖 Table of Contents
1. [What's New (Phase 11)](#-whats-new-phase-11)
2. [Internal Architecture](#-internal-architecture)
3. [Master Tool Suite](#-master-tool-suite)
4. [Advanced Configuration](#-advanced-configuration)
5. [Troubleshooting](#-troubleshooting)

---

## 🚀 What's New (Phase 11)

### 1. Vision-Powered Browser (`browser-use`)
The agent no longer guesses CSS selectors blindly. It now:
- **Sees** the webpage using screenshots.
- **Analyzes** interactive elements visually.
- **Navigates** complex SPAs (Single Page Applications) like YouTube, Gmail, or Stock dashboards effortlessly.

### 2. Context Injection ("The Eyes")
Before every decision, the agent injects the **current browser state** (URL, Title, Screenshot) directly into its thinking process. It never gets "lost" or forgets which tab is open.

### 3. Dynamic Prompting ("The Brain")
The system prompt adapts in real-time:
- **Browser Mode**: Activated when browsing, focusing on visual navigation.
- **Coder Mode**: Activated when writing code, focusing on syntax and logic.

### 4. Sandbox Python Execution
New `PythonTool` allows the agent to execute Python code safely for calculations, data analysis, and logic verification.

---

## 🏗️ Internal Architecture

The engine operates on the OpenManus "ToolCall" loop:

```mermaid
graph TD
    A[Start Step] --> B{Browser Active?}
    B -->|Yes| C[Capture Screenshot & DOM]
    B -->|No| D[Standard Prompt]
    C --> E[Inject Context into Prompt]
    D --> E
    E --> F[LLM Thinking (Vision-Aware)]
    F -->|Tool Call| G[Execute Tool]
    G --> A
```

### Key Modules:
- **`agent_core.py`**: The new brain. Implements `ManusCompetition` agent and `BrowserContextHelper`.
- **`tools/browser_use_tool.py`**: The vision-browser engine tailored for this agent.
- **`llm.py`**: Decoupled LLM client handling failovers and tool calls.
- **`schema.py`**: The Guardian. Validates data and sanitizes every single byte (Phase 10 Hardening).

---

## 🛠️ Master Tool Suite

### 🌐 `browser_use` (The New Standard)
Interacts with the web using the `browser-use` library.
- **Capabilities**: `go_to_url`, `click_element`, `input_text`, `scroll`, `extract_content`, `switch_tab`.
- **Intelligence**: Automatically finds elements based on visual descriptions.

### 🐍 `python_execute` (New!)
Executes Python code in a sandboxed process.
- **Use Case**: Math, string manipulation, data parsing, logic verification.

### 💻 `terminal` (System Integration)
Executes native shell commands.
- **Hardening**: Auto-quotes paths with spaces.

### 🔍 `search` (Real-time Intel)
Powered by Google/Tavily for deep web searching.

---

## ⚙️ Advanced Configuration

All parameters are managed via `config.toml` (same as before), but now supports the new modules.

### Install Dependencies
```bash
pip install -r requirements.txt
playwright install
```

### Run the Agent
```bash
python main.py
```
You will see the new "Manus-Củ-Sen ULTIMATE" banner.

---

## ❓ Troubleshooting

**Q: "NameError: name 'List' is not defined"**
A: Fixed in the latest update of `base_tool.py`.

**Q: Browser not opening?**
A: Ensure you have run `playwright install`. The `browser-use` tool will try to launch a headful browser by default for you to see the action.

**Q: 400 Bad Request Errors?**
A: Our Phase 10 "Absolute Sanitization" layer is still active, protecting the agent from token leakage even with the new brain.

---

*"Manus-Củ-Sen: Now with the Brain of OpenManus and the Heart of Steel."*
