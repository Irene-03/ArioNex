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
import threading
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
        self.failed_proxies: set = set()
        self._lock = threading.Lock()
        logger.info(f"Initialized StaticListProxyProvider with {len(self.proxies)} proxies.")

    def get_proxy(self) -> Optional[str]:
        with self._lock:
            if not self.proxies:
                return None
            # حذف پروکسی‌های ناموفق از لیست انتخاب
            available = [p for p in self.proxies if p not in self.failed_proxies]
            if not available:
                # اگر همه پروکسی‌ها ناموفق بودند، ریست می‌کنیم
                logger.warning("All proxies have failed. Resetting failed proxies list.")
                self.failed_proxies.clear()
                available = self.proxies.copy()
            # انتخاب تصادفی پروکسی برای توزیع بار
            selected = random.choice(available)
            logger.debug(f"Rotating proxy selected: {selected}")
            return selected

    def report_failure(self, proxy: str) -> None:
        """ثبت thread-safe یک پروکسی ناموفق"""
        with self._lock:
            self.failed_proxies.add(proxy)
            logger.warning(f"Proxy marked as failed: {proxy}. Total failed: {len(self.failed_proxies)}/{len(self.proxies)}")

    def reset_failures(self) -> None:
        """ریست کردن لیست پروکسی‌های ناموفق"""
        with self._lock:
            self.failed_proxies.clear()
            logger.info("Proxy failure list has been reset.")

