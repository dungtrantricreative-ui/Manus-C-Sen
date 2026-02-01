import asyncio
import base64
import json
from typing import ClassVar, Dict, Generic, Optional, TypeVar

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from config import settings
from llm import LLM
from base_tool import BaseTool, ToolResult
from tools.search import SearchTool

_BROWSER_DESCRIPTION = """\
Browser automation tool for web page interaction. After EVERY action, you receive:
1. A SCREENSHOT of the current page
2. Interactive elements with INDEX numbers

**HOW TO USE:**
1. Call go_to_url first to navigate
2. Look at the screenshot and element list returned
3. Use the INDEX number to click/input on elements
4. Always wait for page to load between actions

**ACTIONS:**
- go_to_url: Navigate to a URL (required first step)
- click_element: Click element by INDEX (look at returned list)
- input_text: Type text into input field by INDEX
- scroll_down/scroll_up: Scroll the page
- send_keys: Send keyboard shortcuts (Enter, Escape, Tab)
- extract_content: Get page text content
- get_state: Manually get current screenshot and elements
- read_page: (COST SAVING) Auto-scrolls down entire page and extracts text. Use this for articles!

**EXAMPLE WORKFLOW:**
1. go_to_url → See screenshot + elements "[12] Search box, [15] Login button"
2. input_text(index=12, text="query") → Type in search box
3. click_element(index=15) → Click button

IMPORTANT: Always check the INDEX numbers in the response before clicking!
"""

Context = TypeVar("Context")


class BrowserUseTool(BaseTool, Generic[Context]):
    name: str = "browser_use"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "go_to_url",
                    "click_element",
                    "input_text",
                    "scroll_down",
                    "scroll_up",
                    "scroll_to_text",
                    "send_keys",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "go_back",
                    "web_search",
                    "wait",
                    "extract_content",
                    "switch_tab",
                    "open_tab",
                    "close_tab",
                    "get_state",
                    "read_page",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'go_to_url' or 'open_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element INDEX from the element list (e.g., if you see '[12] Submit button', use index=12)",
            },
            "text": {
                "type": "string",
                "description": "Text for 'input_text' or 'scroll_to_text' actions",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (default 500)",
            },
            "tab_id": {
                "type": "integer",
                "description": "Tab ID for 'switch_tab' action",
            },
            "query": {
                "type": "string",
                "description": "Search query for 'web_search' action",
            },
            "goal": {
                "type": "string",
                "description": "Extraction goal for 'extract_content' action",
            },
            "keys": {
                "type": "string",
                "description": "Keys to send (e.g., 'Enter', 'Escape', 'Tab')",
            },
            "seconds": {
                "type": "integer",
                "description": "Seconds to wait for 'wait' action",
            },
        },
        "required": ["action"],
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    browser: Optional[BrowserUseBrowser] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    dom_service: Optional[DomService] = Field(default=None, exclude=True)
    web_search_tool: SearchTool = Field(default_factory=SearchTool, exclude=True)
    tool_context: Optional[Context] = Field(default=None, exclude=True)
    llm: Optional[LLM] = Field(default_factory=LLM)

    # State tracking
    last_action: str = ""
    action_count: int = 0

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            browser_config_kwargs = {"headless": False, "disable_security": True}
            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        if self.context is None:
            context_config = BrowserContextConfig()
            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context

    async def _get_state_with_screenshot(self, context: BrowserContext, action_msg: str = "") -> ToolResult:
        """Get current browser state with screenshot and interactive elements."""
        try:
            state = await context.get_state()
            page = await context.get_current_page()
            
            # Take screenshot
            screenshot = await page.screenshot(full_page=False, type="jpeg", quality=80)
            b64_img = base64.b64encode(screenshot).decode("utf-8")
            
            # Get interactive elements with indices
            elements_str = ""
            if state.element_tree:
                elements_str = state.element_tree.clickable_elements_to_string()
                # Limit length
                if len(elements_str) > 3000:
                    elements_str = elements_str[:3000] + "\n... [truncated]"
            
            # Build comprehensive state info
            output_parts = []
            if action_msg:
                output_parts.append(f"✅ {action_msg}")
            
            output_parts.append(f"\n📍 **URL:** {state.url}")
            output_parts.append(f"📄 **Title:** {state.title}")
            
            if elements_str:
                output_parts.append(f"\n🖱️ **Interactive Elements (use INDEX to click/input):**\n{elements_str}")
            else:
                output_parts.append("\n⚠️ No interactive elements found on this page.")
            
            output_parts.append("\n💡 **Next step:** Look at the screenshot and use the INDEX numbers above to interact!")
            
            return ToolResult(
                output="\n".join(output_parts),
                base64_image=b64_img
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get state: {e}")

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        tab_id: Optional[int] = None,
        query: Optional[str] = None,
        goal: Optional[str] = None,
        keys: Optional[str] = None,
        seconds: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        async with self.lock:
            try:
                context = await self._ensure_browser_initialized()
                self.action_count += 1
                self.last_action = action

                # Handle web_search separately (no browser state needed)
                if action == "web_search":
                    if not query:
                        return ToolResult(error="Query is required for 'web_search' action")
                    search_response = await self.web_search_tool.execute(query=query)
                    return ToolResult(output=search_response)

                # Handle get_state
                if action == "get_state":
                    return await self._get_state_with_screenshot(context, "Current page state:")

                # Navigation actions
                if action == "go_to_url":
                    if not url:
                        return ToolResult(error="URL is required for 'go_to_url' action")
                    page = await context.get_current_page()
                    await page.goto(url)
                    await page.wait_for_load_state()
                    await asyncio.sleep(1)  # Wait for dynamic content
                    return await self._get_state_with_screenshot(context, f"Navigated to {url}")

                elif action == "read_page":
                    # COST EFFICIENT READING: Scroll down multiple times then extract
                    # This saves huge vision tokens and reasoning steps
                    page = await context.get_current_page()
                    
                    # Scroll 3 times
                    for i in range(3):
                        await context.execute_javascript("window.scrollBy(0, 800);")
                        await asyncio.sleep(0.5)
                    
                    # Extract content
                    import markdownify
                    content = markdownify.markdownify(await page.content())
                    if len(content) > 6000:
                        content = content[:6000] + "\n... [truncated]"
                        
                    return ToolResult(output=f"📖 Smart Read (Auto-Scrolled & Extracted):\n{content}")

                elif action == "go_back":
                    await context.go_back()
                    await asyncio.sleep(0.5)
                    return await self._get_state_with_screenshot(context, "Navigated back")

                elif action == "refresh":
                    await context.refresh_page()
                    await asyncio.sleep(1)
                    return await self._get_state_with_screenshot(context, "Refreshed page")

                # Element interaction actions
                elif action == "click_element":
                    if index is None:
                        return ToolResult(error="INDEX is required! Look at the element list and use the number in brackets, e.g., index=12")
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found. Use 'get_state' to see current elements.")
                        await context._click_element_node(element)
                        await asyncio.sleep(1)  # Wait for any page changes
                        return await self._get_state_with_screenshot(context, f"Clicked element at index {index}")
                    except Exception as e:
                        return ToolResult(error=f"Click failed: {e}. Try a different index or use 'get_state' first.")

                elif action == "input_text":
                    if index is None or not text:
                        return ToolResult(error="INDEX and text are required! e.g., index=12, text='hello'")
                    try:
                        element = await context.get_dom_element_by_index(index)
                        if not element:
                            return ToolResult(error=f"Element with index {index} not found.")
                        await context._input_text_element_node(element, text)
                        await asyncio.sleep(0.5)
                        return await self._get_state_with_screenshot(context, f"Typed '{text}' into element {index}")
                    except Exception as e:
                        return ToolResult(error=f"Input failed: {e}")

                elif action == "scroll_down" or action == "scroll_up":
                    direction = 1 if action == "scroll_down" else -1
                    amount = scroll_amount if scroll_amount is not None else 500
                    await context.execute_javascript(f"window.scrollBy(0, {direction * amount});")
                    await asyncio.sleep(0.3)
                    return await self._get_state_with_screenshot(context, f"Scrolled {'down' if direction > 0 else 'up'} {amount}px")

                elif action == "scroll_to_text":
                    if not text:
                        return ToolResult(error="Text is required")
                    page = await context.get_current_page()
                    locator = page.get_by_text(text, exact=False)
                    await locator.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    return await self._get_state_with_screenshot(context, f"Scrolled to text: '{text}'")

                elif action == "send_keys":
                    if not keys:
                        return ToolResult(error="Keys are required (e.g., 'Enter', 'Escape')")
                    page = await context.get_current_page()
                    await page.keyboard.press(keys)
                    await asyncio.sleep(0.5)
                    return await self._get_state_with_screenshot(context, f"Sent keys: {keys}")

                # Content extraction
                elif action == "extract_content":
                    if not goal:
                        return ToolResult(error="Goal is required (what content to extract)")
                    page = await context.get_current_page()
                    import markdownify
                    content = markdownify.markdownify(await page.content())
                    if len(content) > 4000:
                        content = content[:4000] + "\n... [truncated]"
                    return ToolResult(output=f"📝 Extracted content for '{goal}':\n{content}")

                # Tab management
                elif action == "switch_tab":
                    if tab_id is None:
                        return ToolResult(error="Tab ID required")
                    await context.switch_to_tab(tab_id)
                    await asyncio.sleep(0.5)
                    return await self._get_state_with_screenshot(context, f"Switched to tab {tab_id}")

                elif action == "open_tab":
                    if not url:
                        return ToolResult(error="URL required")
                    await context.create_new_tab(url)
                    await asyncio.sleep(1)
                    return await self._get_state_with_screenshot(context, f"Opened new tab: {url}")

                elif action == "close_tab":
                    await context.close_current_tab()
                    return ToolResult(output="Closed current tab")

                elif action == "wait":
                    wait_time = seconds or 3
                    await asyncio.sleep(wait_time)
                    return await self._get_state_with_screenshot(context, f"Waited {wait_time} seconds")

                else:
                    return ToolResult(error=f"Unknown action: {action}. Valid actions: go_to_url, click_element, input_text, scroll_down, etc.")

            except Exception as e:
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def get_current_state(self, context: Optional[BrowserContext] = None) -> ToolResult:
        """Public method to get current state."""
        try:
            ctx = context or self.context
            if not ctx:
                return ToolResult(error="Browser context not initialized. Call go_to_url first.")
            return await self._get_state_with_screenshot(ctx)
        except Exception as e:
            return ToolResult(error=f"Failed to get state: {e}")

    async def cleanup(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
