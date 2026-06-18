"""
/// <summary>
/// ماژول کرالر وب آریونکس
/// </summary>
/// <remarks>
/// از lazy loading برای جلوگیری از مشکلات circular import استفاده می‌کند.
/// </remarks>
"""

from app.services.workers.crawler.engine import CrawlerService

# ایجاد instance به صورت lazy
_crawler_service = None


def get_crawler_service() -> CrawlerService:
    """
    دریافت instance سرویس کرالر با lazy loading.
    از این الگو برای جلوگیری از مشکلات import در زمان startup استفاده می‌شود.
    """
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service


# برای سازگاری با کدهای قبلی که مستقیماً crawler_service را import می‌کنند
crawler_service = get_crawler_service()

__all__ = ['CrawlerService', 'crawler_service', 'get_crawler_service']
