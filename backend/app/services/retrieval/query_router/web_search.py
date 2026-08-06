import logging
import requests
from app.core.config import settings

logger = logging.getLogger("arionex.query_router")

def _get_active_api_key(provider: str) -> str:
    """
    /// <summary>
    /// Map the active provider to its corresponding API key in settings
    /// </summary>
    /// <param name="provider">Name of the active provider (openrouter, openai, hormouz, ...)</param>
    /// <returns>The stored API key value for this provider</returns>
    """
    mapping = {
        "openrouter": settings.openrouter_api_key,
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "google": settings.google_api_key,
        "deepseek": settings.deepseek_api_key,
        "gapgpt": settings.gapgpt_api_key,
        "avalai": settings.avalai_api_key,
        "hormouz": settings.hormouz_api_key,
    }
    return mapping.get(provider, settings.openai_api_key)


def perform_tavily_web_search(query: str) -> list[dict]:
    """
    /// <summary>
    /// Perform a live web search with the Tavily API if it is enabled in the system
    /// </summary>
    /// <param name="query">User question</param>
    /// <returns>List of retrieved web results</returns>
    """
    if not settings.services.web_search or not settings.tavily_api_key or "your-tavily" in settings.tavily_api_key:
        logger.info("Tavily Web Search is disabled or API Key is missing. Skipping web search.")
        return []
        
    logger.info(f"Initiating live Tavily web search for: '{query}'...")
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False
        }
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            web_results = []
            for item in data.get("results", []):
                web_results.append({
                    "content": item.get("content", ""),
                    "label": f"Web Source: {item.get('title', 'External Page')}",
                    "file_id": 999, # Fixed ID for web sources to track frontend metadata
                    "sequence_id": 0,
                    "similarity": 0.65, # Fixed similarity score for web sources
                    "source_type": "web"
                })
            logger.info(f"Tavily search retrieved {len(web_results)} pages.")
            return web_results
    except Exception as e:
        logger.error(f"Tavily Web Search API request failed: {str(e)}")
        
    return []
