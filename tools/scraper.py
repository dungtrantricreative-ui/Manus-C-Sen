import httpx
from bs4 import BeautifulSoup
from base_tool import BaseTool
from loguru import logger

class ScraperTool(BaseTool):
    name: str = "scraper"
    description: str = "Extract full text content from a given URL."
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to scrape content from."}
        },
        "required": ["url"]
    }

    async def execute(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text and clean up whitespace
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                # Limit length to avoid token explosion
                return text[:10000] + ("..." if len(text) > 10000 else "")
                
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            return f"Error scraping URL: {str(e)}"
