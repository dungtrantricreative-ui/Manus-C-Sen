import asyncio
import base64
import json
import os
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from agent_core import BaseTool, LLM
from config import settings
from loguru import logger
import markdownify

class BrowserTool(BaseTool):
    name: str = "browser"
    description: str = """A powerful browser tool. 
    MANDATORY for interaction: Use action='step' with your goal in 'text' parameter. 
    The 'step' action uses a specialized Maverick Vision model to handle clicks/types perfectly.
    Other actions: go_to_url (start here), extract (get text), close."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string", 
                "enum": ["go_to_url", "click", "type", "scroll", "extract", "refresh", "back", "close"],
                "description": "The action to perform."
            },
            "url": {"type": "string", "description": "The URL to navigate to."},
            "selector": {"type": "string", "description": "CSS selector or text for click/type (optional if index provided)."},
            "text": {"type": "string", "description": "Text to type or goal for extraction."},
            "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction."},
            "index": {"type": "integer", "description": "Element index (if using vision-assisted browsing)."}
        },
        "required": ["action"]
    }

    _playwright = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None
    _llm: Optional[LLM] = None

    class Config:
        arbitrary_types_allowed = True

    async def _init_browser(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(headless=False)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
        if not self._page or self._page.is_closed():
            self._page = await self._context.new_page()
        
        if not self._llm:
            self._llm = LLM()

    async def execute(self, action: str, url: Optional[str] = None, selector: Optional[str] = None, 
                      text: Optional[str] = None, direction: str = "down", index: Optional[int] = None) -> str:
        await self._init_browser()
        
        try:
            if action == "go_to_url":
                if not url: return "Error: URL missing"
                if not url.startswith("http"): url = "https://" + url
                await self._page.goto(url, wait_until="networkidle", timeout=30000)
                return f"Navigated to {url}. Title: {await self._page.title()}"

            if action == "step":
                if not text: return "Error: Goal text required for 'step' action."
                
                # Vision-Specialist Step (Maverick)
                screenshot = await self.get_screenshot_base64()
                dom = await self.get_simplified_dom()
                
                prompt = f"""You are a Browser Vision Specialist. Your goal is: {text}
                Current URL: {self._page.url}
                Interactive Elements (Simplified): {json.dumps(dom)}
                
                Analyze the goal and the browser state. Decide the next tech action.
                Return ONLY valid JSON: {{"action": "click|type|scroll|done", "selector": "css_selector", "text": "text_if_typing", "reason": "why"}}
                """
                
                messages = [
                    {"role": "system", "content": "You are a specialized vision-browser agent."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot}"}}
                    ]}
                ]
                
                decision_str = await self._llm.quick_ask(messages, model=settings.VISION_MODEL_NAME)
                # Cleanup JSON in case model adds markers
                decision_str = decision_str.strip().replace("```json", "").replace("```", "")
                decision = json.loads(decision_str)
                
                # Execute the Maverick's decision
                mv_action = decision.get("action")
                mv_selector = decision.get("selector")
                mv_text = decision.get("text")
                
                logger.info(f"Maverick Decision: {mv_action} on {mv_selector} (Reason: {decision.get('reason')})")
                
                if mv_action == "click":
                    await self._page.click(mv_selector, timeout=10000)
                    return f"Maverick Action: Clicked {mv_selector}. Reason: {decision.get('reason')}"
                elif mv_action == "type":
                    await self._page.fill(mv_selector, mv_text, timeout=10000)
                    return f"Maverick Action: Typed into {mv_selector}. Reason: {decision.get('reason')}"
                elif mv_action == "scroll":
                    await self._page.evaluate("window.scrollBy(0, 600)")
                    return "Maverick Action: Scrolled down."
                elif mv_action == "done":
                    return f"Maverick reports goal completed: {decision.get('reason')}"
                
                return f"Maverick decided unknown action: {mv_action}"

            if action == "close":
                await self._browser.close()
                self._browser = None
                return "Browser closed."

            if not self._page or self._page.url == "about:blank":
                return "Error: No page open. Use go_to_url first."

            if action == "refresh":
                await self._page.reload()
                return "Page refreshed."

            if action == "back":
                await self._page.go_back()
                return "Navigated back."

            if action == "scroll":
                amount = 600 if direction == "down" else -600
                await self._page.evaluate(f"window.scrollBy(0, {amount})")
                return f"Scrolled {direction}."

            if action == "extract":
                content = await self._page.content()
                md = markdownify.markdownify(content, heading_style="ATX")
                return f"URL: {self._page.url}\nCONTENT:\n{md[:10000]}"

            # Manual override interactions (click, type)
            if action == "click":
                if not selector: return "Error: Selector or text required."
                try:
                    await self._page.click(selector, timeout=10000)
                except:
                    # Fallback to search by text
                    try:
                        await self._page.get_by_text(selector).first.click(timeout=5000)
                    except:
                        # Fallback to role search
                        await self._page.get_by_role("button", name=selector).first.click(timeout=5000)
                return f"Clicked '{selector}'."

            if action == "type":
                if not selector or not text: return "Error: Selector and text required."
                try:
                    await self._page.fill(selector, text, timeout=10000)
                except:
                    try:
                        # Google uses 'q' name for textarea or input
                        await self._page.locator(f'input[name="{selector}"], textarea[name="{selector}"]').first.fill(text, timeout=5000)
                    except:
                        await self._page.get_by_placeholder(selector).first.fill(text, timeout=5000)
                return f"Typed '{text}' into '{selector}'."

            return f"Error: Unknown action {action}"

        except Exception as e:
            logger.error(f"BrowserTool Error: {e}")
            return f"Error: {str(e)}"

    async def get_screenshot_base64(self) -> str:
        if not self._page: return ""
        screenshot = await self._page.screenshot(type="jpeg", quality=70)
        return base64.b64encode(screenshot).decode('utf-8')

    async def get_simplified_dom(self) -> List[Dict[str, Any]]:
        """Simplified DOM for Llama-4-Maverick browser control"""
        if not self._page: return []
        # Basic logic: Get all interactive elements (buttons, links, inputs)
        elements = await self._page.evaluate("""
            () => {
                const interactives = Array.from(document.querySelectorAll('button, a, input, select, textarea, [role="button"]'));
                return interactives.map((el, i) => ({
                    index: i,
                    tag: el.tagName,
                    text: el.innerText.trim() || el.value || el.placeholder || '',
                    type: el.type || '',
                    role: el.getAttribute('role') || ''
                })).filter(el => el.text.length > 0 || el.tag === 'INPUT').slice(0, 50); // Limit to top 50 for cost
            }
        """)
        return elements

    async def cleanup(self):
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
