import asyncio
import logging
from typing import List, Optional
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)
_PROBE_URL = "https://www.google.com/generate_204"


class CurlProxyValidator:
    async def validate_curl_socks5(
        self, proxy: str, target_url: str = _PROBE_URL, timeout: int = 10
    ) -> bool:
        try:
            async with AsyncSession() as s:
                r = await s.get(
                    target_url, proxy=proxy, impersonate="chrome", timeout=timeout
                )
                return r.status_code < 500
        except Exception as e:
            logger.debug("[CurlValidator] %s rejected: %s", proxy, e)
            return False


async def score_proxies_for_curl(
    proxies: List[str],
    target: str,
    concurrency: int = 50,
    timeout: int = 10,
    validator: Optional[CurlProxyValidator] = None,
) -> List[str]:
    if validator is None:
        validator = CurlProxyValidator()
    sem = asyncio.Semaphore(concurrency)
    valid: List[str] = []

    async def check(p: str) -> None:
        async with sem:
            if await validator.validate_curl_socks5(p, target, timeout):
                valid.append(p)

    await asyncio.gather(*[check(p) for p in proxies])
    logger.info("[CurlValidator] %d/%d proxies passed curl SOCKS5 check", len(valid), len(proxies))
    return valid
