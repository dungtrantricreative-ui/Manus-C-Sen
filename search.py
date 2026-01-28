from tavily import TavilyClient
from config import settings
from loguru import logger

def search_tool(query: str) -> str:
    """
    Search the web for information using Tavily API.
    Returns a text summary of the search results.
    """
    if not settings.TAVILY_API_KEY:
        return "Error: TAVILY_API_KEY not found in environment variables."
    
    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        logger.info(f"Searching for: {query}")
        # Search for context and return as a single string
        response = client.search(query=query, search_depth="advanced")
        
        results = []
        for result in response.get('results', []):
            results.append(f"Title: {result.get('title')}\nURL: {result.get('url')}\nContent: {result.get('content')}\n")
        
        return "\n---\n".join(results) if results else "No results found."
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error during search: {str(e)}"
