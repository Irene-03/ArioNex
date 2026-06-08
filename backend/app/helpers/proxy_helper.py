"""
/// <summary>
/// مدیریت و چرخش پروکسی‌ها (Proxy Rotation & Provider Abstraction)
/// </summary>
/// <remarks>
/// این ماژول ساختار منعطف و انتزاعی برای مدیریت پروکسی‌ها فراهم می‌کند.
/// شامل اینترفیس BaseProxyProvider و کلاس StaticListProxyProvider.
/// </remarks>
"""

import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, List

logger = logging.getLogger("arionex.proxy_helper")

class BaseProxyProvider(ABC):
    """
    /// <summary>
    /// کلاس انتزاعی پایه برای تامین پروکسی (Abstract Base Proxy Provider)
    /// </summary>
    """
    @abstractmethod
    def get_proxy(self) -> Optional[str]:
        """
        /// <summary>
        /// دریافت آدرس یک پروکسی به صورت چرخشی یا تصادفی
        /// </summary>
        /// <returns>آدرس پروکسی به صورت رشته یا None</returns>
        """
        pass

    @abstractmethod
    def report_failure(self, proxy: str) -> None:
        """
        /// <summary>
        /// گزارش عدم پاسخ‌دهی پروکسی برای اهداف آماری یا حذف موقت
        /// </summary>
        """
        pass


class StaticListProxyProvider(BaseProxyProvider):
    """
    /// <summary>
    /// تأمین‌کننده پروکسی بر اساس لیست دستی استاتیک لود شده از کانفیگ
    /// </summary>
    """
    def __init__(self, proxies: List[str]):
        # پاکسازی آدرس پروکسی‌ها
        self.proxies = [p.strip() for p in proxies if p and p.strip()]
        logger.info(f"Initialized StaticListProxyProvider with {len(self.proxies)} proxies.")

    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        # انتخاب تصادفی پروکسی برای توزیع بار
        selected = random.choice(self.proxies)
        logger.debug(f"Rotating proxy selected: {selected}")
        return selected

    def report_failure(self, proxy: str) -> None:
        logger.warning(f"Proxy failed to respond: {proxy}. This can be used to prune/blacklist in future expansions.")
