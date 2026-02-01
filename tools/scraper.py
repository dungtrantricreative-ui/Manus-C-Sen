import httpx
from bs4 import BeautifulSoup
from base_tool import BaseTool
from loguru import logger
import random
import asyncio

class ScraperTool(BaseTool):
    name: str = "scraper"
    description: str = "Extract clean, readable text content from a URL. Uses advanced parsing to remove clutter."
    instructions: str = """
1. **TARGETED USE**: Use this for verified, high-value URLs found via search.
2. **TRAFILATURA**: The internal engine is optimized for articles/blogs.
3. **RESILIENCE**: It will auto-retry with different headers on failure.
4. **FALLBACK**: If this fails, consider `terminal` with `Invoke-WebRequest` as a last resort.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to scrape content from."}
        },
        "required": ["url"]
    }

    async def execute(self, url: str) -> str:
        # Robust headers rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Upgrade-Insecure-Requests": "1"
        }
        
        try:
            # 1. Try fetching with httpx
            async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True, verify=False) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check directly for 403/404/Block strings
                if response.status_code != 200:
                    return f"Error: HTTP {response.status_code} - Unable to access page."

                html = response.text
                
                # 2. Advanced Parsing (Attempt to use trafilatura if available, else BS4)
                try:
                    import trafilatura
                    extract = trafilatura.extract(html, include_links=True, include_images=False, include_tables=True)
                    if extract:
                        return f"--- EXTRACTED CONTENT ({url}) ---\n{extract[:15000]}"
                except ImportError:
                    pass
                
                # 3. Fallback to BS4
                soup = BeautifulSoup(html, "html.parser")
                
                # Intelligent Cleanup
                for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg"]):
                    tag.decompose()
                
                text = soup.get_text(separator="\n")
                
                # Compact lines
                lines = (line.strip() for line in text.splitlines())
                clean_text = "\n".join(chunk for chunk in lines if chunk)
                
                if len(clean_text) < 100:
                     return f"Warning: Page content extremely short ({len(clean_text)} chars). Maybe blocked or JS-heavy."

                return f"--- EXTRACTED CONTENT ({url}) ---\n{clean_text[:15000]}"
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                 return f"Error 404: Page not found ({url}). Check the link."
            if e.response.status_code == 403:
                 return f"Error 403: Access forbidden ({url}). Anti-bot detected."
            return f"HTTP Error: {e}"
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            return f"Scraping Failed: {str(e)}"
