# Manus Prime User Guide (Brain Transplant Edition)

## 1. Introduction

Manus Prime is one of the most advanced autonomous AI agents, designed to execute tasks with high accuracy and optimal efficiency. This project represents a step toward "Superintelligence" (Phase 13). This release deeply integrates core logic from the OpenManus (Event system), Plandex (Planning ledger), and OpenHands (Host execution) projects, providing a solid foundation for complex operations.

Manus Prime operates on a continuous feedback loop: the agent constantly observes the environment via `browser-use`, plans via the `planning` tool, and executes directly on the system (Host Access).

## 2. Key Features

Manus Prime is equipped with a range of advanced capabilities:

* **Event-Driven Core:** Inherited from the OpenHands architecture, all actions and observations are recorded in the EventBus.
* **Strategic Planning:** Integrates Plandex’s ledger logic to manage long-term tasks.
* **Native Host Execution:** Removes sandboxing, enabling the AI to interact directly with PowerShell and Python on the actual machine.
* **Visual Browser:** Uses `browser-use` with an interactive INDEX map.

## 3. Internal Architecture

Manus-C-Sen ULTIMATE runs on OpenManus’s "ToolCall" loop. Below is a detailed description of the main modules:

Manus-C-Sen ULTIMATE is built around OpenManus’s "ToolCall" loop, with its core modules clearly organized. **`agent_core.py`** serves as the agent’s new "brain", implementing the `ManusCompetition` agent and `BrowserContextHelper`, managing thought flows, actions, and tool interactions.

**`tools/browser_use_tool.py`** is a customized visual browser tool that enables advanced interactions with web pages. **`llm.py`** handles LLM clients, including fallback mechanisms and tool invocation, while integrating usage tracking and caching to optimize costs.

**`schema.py`** defines main data structures such as `Message`, `AgentState`, `ToolCall`, `Function`, and `Memory`, and performs validation and sanitization to ensure safety. **`config.py`** manages agent configuration, including LLM settings, enabled tools, cache settings, memory, and monitoring. Finally, **`prompts.py`** contains focused prompt templates, supporting chain-of-thought (CoT) reasoning and adaptive complexity to guide the agent’s decision-making.

## 4. Master Tool Suite

Manus-C-Sen ULTIMATE uses a diverse toolset to perform a variety of tasks:

Manus-C-Sen ULTIMATE employs a diverse toolkit for different tasks, each designed with specific purposes and usage guidance:

**`browser_use` (The new standard)** is the primary tool for interacting with the web via the `browser-use` library. It provides comprehensive capabilities such as `go_to_url` for navigating to a specific URL, `click_element` for interacting elements, `input_text` for entering text into fields, `scroll` for page scrolling, `extract_content` for content extraction, and `switch_tab` for changing browser tabs. This tool is especially intelligent with automatic element discovery based on visual descriptions, helping the agent interact with complex websites efficiently. Usage guidance emphasizes always calling `go_to_url` first to establish context, then analyzing the returned screenshot and element list to determine the correct `INDEX` for click or input actions. It is important to always wait for the page to finish loading between actions to ensure accuracy and avoid errors.

**`python_execute` (New!)** is a powerful tool designed to execute Python code in a secure sandboxed process. It’s ideal for tasks including complex data analysis, precise mathematical computations, efficient string manipulations, and programmatic logic verification. A key note is that only console-printed output is recorded and returned. The execution environment is sandboxed, allowing standard Python libraries but potentially restricting external network access for safety. Thus, this tool is particularly useful for tasks requiring intensive data processing or computations that are hard to express or perform via natural language.

**`terminal` (System-integrated)** is a flexible tool that allows the agent to run native shell commands, providing the ability to execute most system commands such as Python, pip, git, curl, or PowerShell. This tool is especially useful for installing packages, managing files, and serves as a reliable fallback when specialized tools fail. Usage guidance stresses always using non-interactive or auto-accept flags (e.g., `winget install --accept-package-agreements`, `choco install -y`, `pip install --quiet`) to avoid manual confirmation prompts. For multimedia-related tasks, agents are instructed to use `yt-dlp` for all video downloads and `ffmpeg` for all media conversions. On Windows, preferring PowerShell syntax is mandatory to ensure compatibility and optimal efficiency.

**`search_tool` (Real-time information)** is an essential tool for web searches and serves as the primary interface for the agent to access external knowledge. To optimize search effectiveness, if an initial query fails, users should simplify it and focus on specific keywords rather than long natural-language questions. This tool is designed to automatically try multiple search providers in priority order (Tavily -> DuckDuckGo -> Google) to ensure the most comprehensive results. After receiving search results, the recommended next step is to use the `scraper` tool on the most promising URLs to extract detailed information.

**`scraper` (Web content extraction)** is a specialized tool for extracting clean, readable text content from a specific URL. It uses advanced parsing techniques to remove unnecessary elements like ads, navigation menus, and other UI components, keeping only the core content. This tool should be used selectively on verified, high-value URLs discovered via the search tool. To increase reliability, `scraper` will automatically retry with different HTTP headers if initial attempts fail, helping bypass some basic anti-bot measures.

**`file_ops` (File operations)** provides essential functions to interact with the filesystem. It enables the agent to perform operations like reading file contents, writing data to files (create or overwrite), and listing files or directories at a specified path. This tool supports absolute paths, giving flexibility in resource management on the system.

Finally, **`knowledge` (Knowledge base)** is an important tool that serves as the agent’s local knowledge store. Its main purpose is to save and retrieve successful solutions, lessons learned, or technical insights gathered during operations. This helps the agent save tokens by avoiding repeated searches for known information and resolve repetitive tasks faster. The tool supports three main commands: `save` to store a new knowledge item with a topic and content; `search` to find existing knowledge items by keywords in the topic; and `list` to display all knowledge topics currently in the database.

## 5. Installation and Configuration

To set up and run Manus-C-Sen ULTIMATE, follow these steps:

### 5.1. Environment Variables

To configure necessary environment variables, copy the `.env.example` file to `.env` and fill in the corresponding API keys. This ensures the agent can access LLM services and search providers (e.g., Tavily) correctly.

### 5.2. Install Dependencies

Installing dependencies involves using `pip` to install the Python libraries listed in `requirements.txt` and installing the Playwright browsers. The required commands are:

```shell
pip install -r requirements.txt
playwright install
```

### 5.3. Run the Agent

After installation is complete, the agent can be launched by executing `main.py`:

```shell
python main.py
```

When the agent starts successfully, the user will see the "Manus-C-Sen ULTIMATE" banner and the agent will be ready to receive commands.

## 6. Troubleshooting

During use of Manus-C-Sen ULTIMATE, users may encounter some issues. Below are common questions and fixes:

**Q: Error "NameError: name 'List' is not defined"?**

**A**: This issue was fixed in the latest update of `base_tool.py`. Users should ensure they are using the most recent version of the codebase.

**Q: Browser not launching?**

**A**: To resolve this, ensure you have run `playwright install`. The `browser-use` tool is designed to launch a UI-capable browser by default so users can observe the agent’s actions.

**Q: 400 Bad Request error?**

**A**: This error often relates to the agent’s "Absolute Sanitization" (Phase 10), an active security layer. This layer protects the agent from token leakage, even with the new "brain." If you encounter this error, check your configuration and ensure no sensitive data is being transmitted insecurely.

## 7. Conclusion

Manus-C-Sen ULTIMATE is a significant step forward in autonomous AI agents, offering powerful web interaction, flexible code execution, and intelligent reasoning mechanisms. With a modular architecture and a diverse toolset, it can handle many complex tasks—from web browsing to data analysis and knowledge management. Understanding its features and configuration will help you fully leverage the agent’s power.

---

*"Manus-C-Sen: Now with the Brain of OpenManus and the Heart of Steel."*

## 8. Best Practices when Using Manus-C-Sen ULTIMATE

To maximize effectiveness and avoid unwanted issues when working with Manus-C-Sen ULTIMATE, adhere to the following best practices:

Users should follow several best practices to maximize effectiveness and avoid problems. First, be **clear and specific in requests**—provide unambiguous instructions so the agent can perform optimally. **Verify and validate** the agent’s outputs, especially for critical tasks, to ensure accuracy and alignment with original objectives.

When using `search_tool`, **optimize search queries** by focusing on core keywords and short phrases rather than long questions to improve relevance. Likewise, **use `scraper` selectively** on verified URLs to avoid reliability or legal concerns.

**Manage environment variables carefully**: ensure API keys and other sensitive information are stored securely in `.env` and not committed to version control. Users should also **monitor usage and costs** via `llm.py`’s features to manage budgets and optimize LLM resource use. Finally, **leverage the `knowledge` store** to save solutions and useful information to save tokens and speed up recurring tasks. Understand the sandbox limits when using `python_execute` and `terminal`, as external network operations may be restricted and some system commands might not behave as expected.

## 9. Future Development and Improvements

The Manus-C-Sen ULTIMATE project is continuously evolving. Potential future directions include:

The Manus-C-Sen ULTIMATE project is under continuous development with multiple potential directions. One primary focus is **enhancing continual learning**, by developing mechanisms that allow the agent to learn and adapt better to new tasks and changing environments, possibly via reinforcement learning or advanced machine learning techniques.

Expanding the toolset is a priority to integrate more domain-specific tools, such as financial analysis tools, graphic design utilities, or project management tools, broadening the agent’s application scope. **Improving human-AI interaction** is also a key goal, by building more intuitive user interfaces and more natural interaction methods, making it easier for users to instruct and collaborate with the agent.

To ensure sustainability and efficiency, the project will continue **optimizing performance and costs** by refining algorithms and mechanisms to reduce resource consumption (tokens, CPU, memory) while maintaining or improving overall performance. Enhancing **self-healing capabilities** is another important direction, enabling the agent to detect, diagnose, and remediate issues autonomously, reducing human intervention. Finally, **advancing multi-language support** will be emphasized; while Vietnamese is currently supported, improving understanding and high-quality generation across many languages will significantly broaden the user base and application potential for Manus-C-Sen ULTIMATE.

With ongoing improvements, Manus-C-Sen ULTIMATE aims to become an increasingly powerful and flexible AI assistant, capable of tackling complex challenges across many domains.
