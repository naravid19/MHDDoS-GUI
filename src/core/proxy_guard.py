from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger("mhddos_gui.proxy_guard")


@dataclass
class ProxyNode:
    url: str
    failures: int = 0
    is_open: bool = True


class ProxyCircuitBreaker:
    """Asynchronous circuit breaker to evict unstable proxies and prevent connection storms."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._pool: Dict[str, ProxyNode] = {}
        self._lock = asyncio.Lock()

    def is_available(self, proxy_url: str) -> bool:
        node = self._pool.get(proxy_url)
        if node is None:
            return True
        return node.is_open

    def get_healthy_proxies(self, proxy_list: List[str]) -> List[str]:
        return [p for p in proxy_list if self.is_available(p)]

    async def register_success(self, proxy_url: str) -> None:
        async with self._lock:
            node = self._pool.get(proxy_url)
            if node is not None:
                node.failures = 0
                node.is_open = True

    async def register_failure(self, proxy_url: str) -> None:
        async with self._lock:
            node = self._pool.setdefault(proxy_url, ProxyNode(url=proxy_url))
            node.failures += 1
            if node.failures >= self.failure_threshold and node.is_open:
                node.is_open = False
                logger.warning(
                    f"[Circuit Breaker] Evicting proxy {proxy_url} after {node.failures} failures."
                )
                asyncio.create_task(self._schedule_recovery(node))

    async def _schedule_recovery(self, node: ProxyNode) -> None:
        await asyncio.sleep(self.recovery_timeout)
        async with self._lock:
            node.failures = 0
            node.is_open = True
            logger.info(f"[Circuit Breaker] Restored proxy {node.url} to active rotation.")
