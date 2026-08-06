"""
/// <summary>
/// Proxy management and rotation (Proxy Rotation & Provider Abstraction)
/// </summary>
/// <remarks>
/// This module provides a flexible, abstract structure for managing proxies.
/// It includes the BaseProxyProvider interface and the StaticListProxyProvider class.
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
    /// Abstract base class for providing proxies (Abstract Base Proxy Provider)
    /// </summary>
    """
    @abstractmethod
    def get_proxy(self) -> Optional[str]:
        """
        /// <summary>
        /// Gets a proxy address in a rotating or random manner
        /// </summary>
        /// <returns>Proxy address as a string or None</returns>
        """
        pass

    @abstractmethod
    def report_failure(self, proxy: str) -> None:
        """
        /// <summary>
        /// Reports a non-responsive proxy for statistical purposes or temporary removal
        /// </summary>
        """
        pass


class StaticListProxyProvider(BaseProxyProvider):
    """
    /// <summary>
    /// Proxy provider based on a static manual list loaded from configuration
    /// </summary>
    """
    def __init__(self, proxies: List[str]):
        # Clean proxy addresses
        self.proxies = [p.strip() for p in proxies if p and p.strip()]
        self.failed_proxies: set = set()
        self._lock = threading.Lock()
        logger.info(f"Initialized StaticListProxyProvider with {len(self.proxies)} proxies.")

    def get_proxy(self) -> Optional[str]:
        with self._lock:
            if not self.proxies:
                return None
            # Exclude failed proxies from the selection list
            available = [p for p in self.proxies if p not in self.failed_proxies]
            if not available:
                # If all proxies have failed, reset the list
                logger.warning("All proxies have failed. Resetting failed proxies list.")
                self.failed_proxies.clear()
                available = self.proxies.copy()
            # Random proxy selection for load distribution
            selected = random.choice(available)
            logger.debug(f"Rotating proxy selected: {selected}")
            return selected

    def report_failure(self, proxy: str) -> None:
        """Thread-safely records a failed proxy"""
        with self._lock:
            self.failed_proxies.add(proxy)
            logger.warning(f"Proxy marked as failed: {proxy}. Total failed: {len(self.failed_proxies)}/{len(self.proxies)}")

    def reset_failures(self) -> None:
        """Resets the list of failed proxies"""
        with self._lock:
            self.failed_proxies.clear()
            logger.info("Proxy failure list has been reset.")

