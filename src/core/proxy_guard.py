from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger("mhddos_gui.proxy_guard")


@dataclass
class ProxyNode:
    """Represents the state of a single proxy node.

    Attributes:
        url: The URL of the proxy.
        failures: Number of consecutive failures registered.
        is_evicted: Whether the proxy is currently evicted from the rotation.
    """
    url: str
    failures: int = 0
    is_evicted: bool = False


class ProxyCircuitBreaker:
    """Asynchronous circuit breaker to evict unstable proxies and prevent connection storms."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> None:
        """Initialize the ProxyCircuitBreaker.

        Args:
            failure_threshold: Number of failures allowed before evicting a proxy.
            recovery_timeout: Time in seconds to wait before attempting recovery.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._pool: dict[str, ProxyNode] = {}
        self._recovery_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    def is_available(self, proxy_url: str) -> bool:
        """Check if a proxy is healthy and available.

        Args:
            proxy_url: The URL of the proxy to check.

        Returns:
            True if the proxy is healthy/available, False if it is evicted.
        """
        node = self._pool.get(proxy_url)
        if node is None:
            return True
        return not node.is_evicted

    def get_healthy_proxies(self, proxy_list: list[str]) -> list[str]:
        """Filter a list of proxies to return only healthy (not evicted) ones.

        Args:
            proxy_list: List of proxy URLs to filter.

        Returns:
            A new list containing only healthy proxy URLs.
        """
        return [p for p in proxy_list if self.is_available(p)]

    async def register_success(self, proxy_url: str) -> None:
        """Register a successful request with a proxy, resetting its state.

        This cancels any pending recovery task and resets the failure count.

        Args:
            proxy_url: The URL of the proxy that succeeded.
        """
        async with self._lock:
            node = self._pool.get(proxy_url)
            if node is not None:
                node.failures = 0
                node.is_evicted = False
            task = self._recovery_tasks.pop(proxy_url, None)
            if task is not None and not task.done():
                task.cancel()

    async def register_failure(self, proxy_url: str) -> None:
        """Register a failed request with a proxy.

        If failures reach the threshold, evict the proxy and schedule recovery.

        Args:
            proxy_url: The URL of the proxy that failed.
        """
        async with self._lock:
            node = self._pool.setdefault(proxy_url, ProxyNode(url=proxy_url))
            node.failures += 1
            if node.failures >= self.failure_threshold and not node.is_evicted:
                node.is_evicted = True
                logger.warning(
                    f"[Circuit Breaker] Evicting proxy {proxy_url} after {node.failures} failures."
                )
                old_task = self._recovery_tasks.pop(proxy_url, None)
                if old_task is not None and not old_task.done():
                    old_task.cancel()

                task = asyncio.create_task(self._schedule_recovery(node))
                self._recovery_tasks[proxy_url] = task

    async def _schedule_recovery(self, node: ProxyNode) -> None:
        """Schedule a background task to restore the proxy after the cooldown period.

        Args:
            node: The ProxyNode instance to be restored.
        """
        try:
            await asyncio.sleep(self.recovery_timeout)
            async with self._lock:
                current_task = asyncio.current_task()
                if self._recovery_tasks.get(node.url) is current_task:
                    self._recovery_tasks.pop(node.url, None)
                    node.failures = 0
                    node.is_evicted = False
                    logger.info(f"[Circuit Breaker] Restored proxy {node.url} to active rotation.")
        except asyncio.CancelledError:
            logger.debug(f"[Circuit Breaker] Recovery task for {node.url} cancelled.")
            raise
