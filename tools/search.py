from tavily import TavilyClient
from config import settings
from base_tool import BaseTool
from loguru import logger
import asyncio
from duckduckgo_search import DDGS
import requests

class SearchTool(BaseTool):
    name: str = "search_tool"
    description: str = "Perform a web search. The primary interface for external knowledge."
    instructions: str = """
1. **PRIORITY**: Google Custom Search API (High Quality) → Tavily (LLM Optimized) → DuckDuckGo (Free Backup).
2. **QUERY STRATEGY**: If a query fails, simplify it. Don't use natural language questions; use keywords.
3. **NEXT STEP**: After searching, use `scraper` on the most promising URLs found.
4. **LIMITS**: Returns max 5-10 results. Read snippets carefully before scraping.
"""
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The keyword-based search query."}
        },
        "required": ["query"]
    }

    async def execute(self, query: str = "", **kwargs) -> str:
        # Resilient argument handling
        query = query or kwargs.get("text") or kwargs.get("input") or ""
        if not query:
            return "Error: No search query provided."
        
        results = []
        errors = []

        # 1. Google Custom Search API (Priority)
        if settings.GOOGLE_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID:
            # Check if not placeholder
            if settings.GOOGLE_SEARCH_ENGINE_ID != "YOUR_SEARCH_ENGINE_ID_HERE":
                try:
                    url = "https://www.googleapis.com/customsearch/v1"
                    params = {
                        "key": settings.GOOGLE_API_KEY,
                        "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
                        "q": query,
                        "num": 8  # Max 10 results per request
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        google_res = []
                        
                        for item in data.get('items', []):
                            title = item.get('title', 'No title')
                            link = item.get('link', '')
                            snippet = item.get('snippet', 'No description')
                            google_res.append(f"Title: {title}\nLink: {link}\nInfo: {snippet}\n")
                        
                        if google_res:
                            return f"--- Google Custom Search Results ({query}) ---\n" + "\n".join(google_res)
                    elif response.status_code == 429:
                        errors.append("Google API: Quota exceeded (falling back to other providers)")
                    else:
                        errors.append(f"Google API: HTTP {response.status_code}")
                except Exception as e:
                    errors.append(f"Google API: {str(e)}")
            else:
                logger.debug("Google Search Engine ID not configured, skipping Google API")

        # 2. Tavily (Backup #1 - Best for LLMs)
        if settings.TAVILY_API_KEY:
            try:
                client = TavilyClient(api_key=settings.TAVILY_API_KEY)
                response = client.search(query=query, search_depth="advanced")
                tavily_res = []
                for result in response.get('results', []):
                    tavily_res.append(f"Title: {result.get('title')}\nLink: {result.get('url')}\nInfo: {result.get('content')}\n")
                if tavily_res:
                    return f"--- Tavily Search Results ({query}) ---\n" + "\n".join(tavily_res)
            except Exception as e:
                errors.append(f"Tavily: {e}")

        # 3. DuckDuckGo (Backup #2 - Free)
        try:
            with DDGS() as ddgs:
                ddg_gen = ddgs.text(query, max_results=6)
                ddg_res = []
                for r in ddg_gen:
                    ddg_res.append(f"Title: {r.get('title')}\nLink: {r.get('href')}\nInfo: {r.get('body')}\n")
                if ddg_res:
                    return f"--- DuckDuckGo Results ({query}) ---\n" + "\n".join(ddg_res)
        except Exception as e:
             errors.append(f"DDG: {e}")

        # 4. Google Scraper (Last Resort)
        try:
            from googlesearch import search
            google_res = []
            for url in search(query, num_results=5, advanced=True):
                 google_res.append(f"Title: {url.title}\nLink: {url.url}\nInfo: {url.description}")
            
            if google_res:
                 return f"--- Google Scraped Results ({query}) ---\n" + "\n".join(google_res)
        except Exception as e:
            errors.append(f"Google Scraper: {e}")

        return f"Search failed for '{query}'. Errors: {'; '.join(errors)}"
