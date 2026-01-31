import asyncio
import base64
import json
from typing import Generic, Optional, TypeVar

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
A powerful browser automation tool that allows interaction with web pages through various actions.
* This tool provides commands for controlling a browser session, navigating web pages, and extracting information
* It maintains state across calls, keeping the browser session alive until explicitly closed
* Use this when you need to browse websites, fill forms, click buttons, extract content, or perform web searches
* Each action requires specific parameters as defined in the tool's dependencies

Key capabilities include:
* Navigation: Go to specific URLs, go back, search the web, or refresh pages
* Interaction: Click elements, input text, select from dropdowns, send keyboard commands
* Scrolling: Scroll up/down by pixel amount or scroll to specific text
* Content extraction: Extract and analyze content from web pages based on specific goals
* Tab management: Switch between tabs, open new tabs, or close tabs

Note: When using element indices, refer to the numbered elements shown in the current browser state.
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
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'go_to_url' or 'open_tab' actions",
            },
            "index": {
                "type": "integer",
                "description": "Element index for 'click_element', 'input_text', 'get_dropdown_options', or 'select_dropdown_option' actions",
            },
            "text": {
                "type": "string",
                "description": "Text for 'input_text', 'scroll_to_text', or 'select_dropdown_option' actions",
            },
            "scroll_amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive for down, negative for up) for 'scroll_down' or 'scroll_up' actions",
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
                "description": "Keys to send for 'send_keys' action",
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

    # Context for generic functionality
    tool_context: Optional[Context] = Field(default=None, exclude=True)

    llm: Optional[LLM] = Field(default_factory=LLM)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_browser_initialized(self) -> BrowserContext:
        """Ensure browser and context are initialized."""
        if self.browser is None:
            browser_config_kwargs = {"headless": False, "disable_security": True}
            # Simplified config for now
            self.browser = BrowserUseBrowser(BrowserConfig(**browser_config_kwargs))

        if self.context is None:
            context_config = BrowserContextConfig()
            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context

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
                max_content_length = 4000 # Hardcoded safe limit for now

                # Navigation actions
                if action == "go_to_url":
                    if not url: return ToolResult(error="URL is required for 'go_to_url' action")
                    page = await context.get_current_page()
                    await page.goto(url)
                    await page.wait_for_load_state()
                    return ToolResult(output=f"Navigated to {url}")

                elif action == "go_back":
                    await context.go_back()
                    return ToolResult(output="Navigated back")

                elif action == "refresh":
                    await context.refresh_page()
                    return ToolResult(output="Refreshed current page")

                elif action == "web_search":
                    if not query: return ToolResult(error="Query is required for 'web_search' action")
                    search_response = await self.web_search_tool.execute(query=query)
                    return ToolResult(output=search_response)

                # Element interaction actions
                elif action == "click_element":
                    if index is None: return ToolResult(error="Index is required for 'click_element' action")
                    element = await context.get_dom_element_by_index(index)
                    if not element: return ToolResult(error=f"Element with index {index} not found")
                    await context._click_element_node(element)
                    return ToolResult(output=f"Clicked element at index {index}")

                elif action == "input_text":
                    if index is None or not text: return ToolResult(error="Index and text are required for 'input_text' action")
                    element = await context.get_dom_element_by_index(index)
                    if not element: return ToolResult(error=f"Element with index {index} not found")
                    await context._input_text_element_node(element, text)
                    return ToolResult(output=f"Input '{text}' into element at index {index}")

                elif action == "scroll_down" or action == "scroll_up":
                    direction = 1 if action == "scroll_down" else -1
                    amount = scroll_amount if scroll_amount is not None else 600
                    await context.execute_javascript(f"window.scrollBy(0, {direction * amount});")
                    return ToolResult(output=f"Scrolled {'down' if direction > 0 else 'up'} by {amount} pixels")

                elif action == "scroll_to_text":
                    if not text: return ToolResult(error="Text is required")
                    page = await context.get_current_page()
                    locator = page.get_by_text(text, exact=False)
                    await locator.scroll_into_view_if_needed()
                    return ToolResult(output=f"Scrolled to text: '{text}'")

                elif action == "send_keys":
                    if not keys: return ToolResult(error="Keys are required")
                    page = await context.get_current_page()
                    await page.keyboard.press(keys)
                    return ToolResult(output=f"Sent keys: {keys}")
                
                 # Content extraction actions
                elif action == "extract_content":
                    if not goal: return ToolResult(error="Goal is required")
                    page = await context.get_current_page()
                    import markdownify
                    content = markdownify.markdownify(await page.content())
                    return ToolResult(output=f"Extracted content related to '{goal}':\n{content[:max_content_length]}")

                # Tab management
                elif action == "switch_tab":
                    if tab_id is None: return ToolResult(error="Tab ID required")
                    await context.switch_to_tab(tab_id)
                    return ToolResult(output=f"Switched to tab {tab_id}")

                elif action == "open_tab":
                    if not url: return ToolResult(error="URL required")
                    await context.create_new_tab(url)
                    return ToolResult(output=f"Opened new tab with {url}")

                elif action == "close_tab":
                    await context.close_current_tab()
                    return ToolResult(output="Closed current tab")
                
                elif action == "wait":
                    await asyncio.sleep(seconds or 3)
                    return ToolResult(output=f"Waited for {seconds or 3} seconds")

                else:
                    return ToolResult(error=f"Unknown action: {action}")

            except Exception as e:
                return ToolResult(error=f"Browser action '{action}' failed: {str(e)}")

    async def get_current_state(self, context: Optional[BrowserContext] = None) -> ToolResult:
        try:
            ctx = context or self.context
            if not ctx: return ToolResult(error="Browser context not initialized")
            state = await ctx.get_state()
            page = await ctx.get_current_page()
            
            # Screenshot with highlighted elements logic is built-in to browser-use usually, but we take a raw one here
            # Browser-use might have internal highlighting. Let's trust get_state or do our own.
            # Ideally we want the browser-use internal highlighting.
            # For now, let's just get a standard screenshot to be safe.
            screenshot = await page.screenshot(full_page=False, type="jpeg", quality=75)
            b64_img = base64.b64encode(screenshot).decode("utf-8")

            state_info = {
                "url": state.url,
                "title": state.title,
                "tabs": [t.model_dump() for t in state.tabs],
                "interactive_elements": state.element_tree.clickable_elements_to_string() if state.element_tree else ""
            }
            return ToolResult(output=json.dumps(state_info, indent=2), base64_image=b64_img)
        except Exception as e:
            return ToolResult(error=f"Failed to get state: {e}")

    async def cleanup(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
