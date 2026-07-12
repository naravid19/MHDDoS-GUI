import asyncio
import logging
try:
    from curl_cffi.requests import AsyncSession
    _CURL_AVAILABLE = True
except ImportError:
    AsyncSession = None
    _CURL_AVAILABLE = False

from typing import List, Optional

logger = logging.getLogger(__name__)
_PROBE_URL = "https://cloudflare.com/cdn-cgi/trace"

class CurlProxyValidator:
    async def validate_curl_socks5(
        self, proxy: str, target_url: str = _PROBE_URL, timeout: int = 8
    ) -> bool:
        proxy_map = {"http": proxy, "https": proxy}
        try:
            async with AsyncSession(proxies=proxy_map, verify=False, timeout=timeout) as s:
                r = await s.get(_PROBE_URL, impersonate="chrome")
                return r.status_code < 500
        except Exception as e:
            logger.debug("[CurlValidator] %s rejected: %s", proxy, e)
            return False

async def score_proxies_for_curl(
    proxies: List[str],
    target: str,
    concurrency: int = 50,
    timeout: int = 8,
    validator: Optional[CurlProxyValidator] = None,
) -> List[str]:
    if validator is None:
        validator = CurlProxyValidator()
    sem = asyncio.Semaphore(concurrency)
    valid: List[str] = []
    async def check(p: str) -> None:
        async with sem:
            if await validator.validate_curl_socks5(p, _PROBE_URL, timeout):
                valid.append(p)
    await asyncio.gather(*[check(p) for p in proxies])
    logger.info("[CurlValidator] %d/%d proxies passed curl check", len(valid), len(proxies))
    return valid
