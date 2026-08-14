from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional, Set

logger = logging.getLogger("mhddos_gui.proxy_guard")


class ProxyCircuitBreaker:
    """Asynchronous circuit breaker to evict unstable proxies and prevent connection storms.
    
    Maintains compatibility with legacy async register_success/register_failure methods
    and sync is_available method.
    """

    def __init__(self, failure_threshold: int = 2, quarantine_duration: float = 900.0, recovery_timeout: Optional[float] = None) -> None:
        self.failure_threshold = failure_threshold
        self.quarantine_duration = recovery_timeout if recovery_timeout is not None else quarantine_duration
        self.failures: Dict[str, int] = {}
        self.quarantined_until: Dict[str, float] = {}
        self.last_cleanup = 0.0

    def record_failure(self, proxy: str) -> None:
        self.failures[proxy] = self.failures.get(proxy, 0) + 1
        if self.failures[proxy] >= self.failure_threshold:
            self.quarantined_until[proxy] = time.time() + self.quarantine_duration
            logger.warning(
                f"[Circuit Breaker] Evicting/quarantining proxy {proxy} after {self.failures[proxy]} failures."
            )

    def cleanup_expired(self) -> None:
        """Remove expired quarantine entries and enforce a hard cap on failures dict size."""
        now = time.time()
        expired_proxies = [
            proxy for proxy, until in list(self.quarantined_until.items())
            if now >= until
        ]
        for proxy in expired_proxies:
            self.quarantined_until.pop(proxy, None)
            self.failures.pop(proxy, None)
        # Memory-leak guard: if failures dict grows beyond 5000 entries, clear it entirely
        if len(self.failures) > 5000:
            self.failures.clear()
            self.quarantined_until.clear()

    def is_quarantined(self, proxy: str) -> bool:
        now = time.time()
        # Rate-limit full cleanup to once every 15 seconds
        if now - self.last_cleanup > 15.0:
            self.cleanup_expired()
            self.last_cleanup = now

        if proxy in self.quarantined_until:
            if now < self.quarantined_until[proxy]:
                return True
            else:
                self.quarantined_until.pop(proxy, None)
                self.failures.pop(proxy, None)
        return False

    # --- Legacy Compatibility Layer ---
    def is_available(self, proxy_url: str) -> bool:
        """Check if a proxy is healthy and available."""
        return not self.is_quarantined(proxy_url)

    def get_healthy_proxies(self, proxy_list: List[str]) -> List[str]:
        """Filter a list of proxies to return only healthy (not evicted) ones."""
        return [p for p in proxy_list if self.is_available(p)]

    async def register_success(self, proxy_url: str) -> None:
        """Register a successful request with a proxy, resetting its state.
        
        This resets the failure count and removes the quarantine status.
        """
        self.failures[proxy_url] = 0
        self.quarantined_until.pop(proxy_url, None)

    async def register_failure(self, proxy_url: str) -> None:
        """Register a failed request with a proxy."""
        self.record_failure(proxy_url)


class ProxyPoolSilo:
    """Manages separate pools (silos) for HTTP, SOCKS4, and SOCKS5 proxies to prevent cross-protocol corruption."""

    def __init__(self) -> None:
        self.silos: Dict[str, List[str]] = {
            "http": [],
            "socks4": [],
            "socks5": []
        }
        self.circuit_breaker = ProxyCircuitBreaker()
        self.current_indices: Dict[str, int] = {
            "http": 0,
            "socks4": 0,
            "socks5": 0
        }
        self.seen_proxies: Set[str] = set()

    def add_proxies(self, proxy_list: List[str]) -> None:
        """Parses, normalises, and deduplicates raw proxy strings into their protocol silos."""
        for p in proxy_list:
            p = p.strip()
            if not p:
                continue
                
            p_lower = p.lower()
            if p_lower.startswith("socks5://") or p_lower.startswith("socks5h://"):
                if p not in self.seen_proxies:
                    self.seen_proxies.add(p)
                    self.silos["socks5"].append(p)
            elif p_lower.startswith("socks4://") or p_lower.startswith("socks4a://"):
                if p not in self.seen_proxies:
                    self.seen_proxies.add(p)
                    self.silos["socks4"].append(p)
            else:
                if not p_lower.startswith("http://") and not p_lower.startswith("https://"):
                    p = f"http://{p}"
                if p not in self.seen_proxies:
                    self.seen_proxies.add(p)
                    self.silos["http"].append(p)

    def get_proxy(self, protocol: str) -> Optional[str]:
        """Returns a non-quarantined proxy for the specified protocol, rotating through available healthy proxies in a round-robin fashion."""
        protocol = protocol.lower()
        if protocol == "https":
            protocol = "http"
            
        if protocol not in self.silos:
            return None
            
        proxies = self.silos[protocol]
        if not proxies:
            return None
            
        n = len(proxies)
        start_idx = self.current_indices.get(protocol, 0) % n
        
        for i in range(n):
            idx = (start_idx + i) % n
            proxy = proxies[idx]
            if not self.circuit_breaker.is_quarantined(proxy):
                self.current_indices[protocol] = (idx + 1) % n
                return proxy
                
        return None

    def report_failure(self, proxy: str, error_code: str) -> None:
        """Records a failure on a proxy if the error indicates a connection/protocol level failure."""
        critical_errors = {"CURLE_COULDNT_CONNECT", "0x01", "97", "35", "SOCKS_FAILURE", "28", "10061", "TIMEOUT", "CURLE_OPERATION_TIMEDOUT"}
        if error_code in critical_errors or any(code in re.split(r'\W+', error_code) for code in critical_errors):
            self.circuit_breaker.record_failure(proxy)

    def is_quarantined(self, proxy: str) -> bool:
        """Checks if a specific proxy is currently quarantined by the circuit breaker."""
        return self.circuit_breaker.is_quarantined(proxy)
