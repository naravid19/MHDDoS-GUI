import asyncio, logging
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


class TokenManager:
    def __init__(self, waterfall_fn: Optional[Callable[[str], Awaitable[str]]] = None):
        self._token: Optional[str] = None
        self._lock = asyncio.Lock()
        self._solving = False
        self.gate: asyncio.Event = asyncio.Event()
        self._waterfall_fn = waterfall_fn

    async def set_token(self, token: str) -> None:
        self._token = token
        self.gate.set()

    async def get_token(self) -> Optional[str]:
        await self.gate.wait()
        return self._token

    def is_stale_response(self, status_code: int, title: str) -> bool:
        return status_code in (403, 503) and any(
            k in title.lower() for k in ("just a moment", "challenge", "attention required")
        )

    async def invalidate_and_resolve(self, target_url: str) -> None:
        async with self._lock:
            if self._solving:
                return
            self._solving = True
            self.gate.clear()
            self._token = None
        logger.warning("[TokenManager] Token invalidated. Re-solving for %s", target_url)
        try:
            wf = self._waterfall_fn
            if wf is None:
                from src.core.engine import _run_waterfall_bypass
                wf = _run_waterfall_bypass
            new_tok = await wf(target_url)
            if new_tok:
                self._token = new_tok
                logger.info("[TokenManager] Re-solve OK — new token acquired.")
            else:
                logger.error("[TokenManager] Re-solve FAILED — no token returned.")
        except Exception as e:
            logger.error("[TokenManager] Re-solve exception: %s", e)
        finally:
            self._solving = False
            self.gate.set()


_singleton: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    global _singleton
    if _singleton is None:
        _singleton = TokenManager()
    return _singleton
