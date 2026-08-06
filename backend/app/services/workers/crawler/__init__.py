"""
/// <summary>
/// ArioNex Web Crawler module
/// </summary>
/// <remarks>
/// Uses lazy loading to avoid circular import problems.
/// </remarks>
"""

from app.services.workers.crawler.engine import CrawlerService

# Create the instance lazily
_crawler_service = None


def get_crawler_service() -> CrawlerService:
    """
    Get the crawler service instance with lazy loading.
    This pattern is used to avoid import problems at startup time.
    """
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service


# For compatibility with previous code that imports crawler_service directly
crawler_service = get_crawler_service()

__all__ = ['CrawlerService', 'crawler_service', 'get_crawler_service']
