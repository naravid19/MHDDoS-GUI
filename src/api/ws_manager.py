# src/api/ws_manager.py
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict
from fastapi import WebSocket
from pydantic import BaseModel

from src.core.state_manager import state_manager, AttackStateSnapshot

logger = logging.getLogger("mhddos_gui.ws")


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] | AttackStateSnapshot


class ConnectionManager:
    """Production-grade WebSocket manager with concurrent broadcast and auto-reconciliation."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
            client_count = len(self._clients)
        logger.info(f"Client connected. Total clients: {client_count}")

        current_state = await state_manager.get_state()
        await self.send_personal_message(
            WSMessage(type="state_reconcile", payload=current_state),
            websocket,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
            client_count = len(self._clients)
        logger.info(f"Client disconnected. Total clients: {client_count}")

    async def send_personal_message(self, message: WSMessage, websocket: WebSocket) -> None:
        try:
            await websocket.send_json(message.model_dump(mode="json"))
        except Exception as exc:
            logger.warning(f"Failed to send personal message: {exc}")
            await self.disconnect(websocket)

    async def broadcast(self, message: WSMessage) -> None:
        """Concurrent non-blocking broadcast to prevent slow-client lag."""
        async with self._lock:
            target_clients = list(self._clients)

        if not target_clients:
            return

        payload_dict = message.model_dump(mode="json")
        tasks = [client.send_json(payload_dict) for client in target_clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        dead_clients: list[WebSocket] = []
        for client, result in zip(target_clients, results):
            if isinstance(result, Exception):
                logger.warning(f"Removing dead client after broadcast error: {result}")
                dead_clients.append(client)

        if dead_clients:
            async with self._lock:
                for dead in dead_clients:
                    self._clients.discard(dead)


ws_manager = ConnectionManager()


class TelemetryAggregator:
    def __init__(self, emit_interval: float = 1.0):
        self.emit_interval = emit_interval
        self.last_emit = time.time()
        self.ok_count = 0
        self.waf_count = 0
        self.err_count = 0
        self.tmo_count = 0
        self.total_latency = 0.0
        self.probe_count = 0

    def record_probe(self, status: int, is_waf: bool = False, latency_ms: float = 0.0, is_err: bool = False, is_tmo: bool = False) -> None:
        self.probe_count += 1
        if is_waf or status == 403:
            self.waf_count += 1
        elif is_tmo:
            self.tmo_count += 1
        elif is_err or status >= 500:
            self.err_count += 1
        elif status == 200:
            self.ok_count += 1
            
        if latency_ms > 0:
            self.total_latency += latency_ms

    def get_telemetry_frame(self, target: str, method: str) -> Dict[str, Any]:
        now = time.time()
        elapsed = max(now - self.last_emit, 1.0)
        
        pps = int(self.probe_count / elapsed)
        avg_latency = round(self.total_latency / max(self.probe_count, 1), 2)
        
        frame = {
            "timestamp": int(now),
            "target": target,
            "method": method,
            "status": {
                "pps": pps,
                "bps_kb": round(pps * 5.8, 2),
                "latency_ms": avg_latency
            },
            "counters": {
                "ok": self.ok_count,
                "waf": self.waf_count,
                "err": self.err_count,
                "tmo": self.tmo_count
            }
        }
        
        # Reset counters after frame generation
        self.last_emit = now
        self.probe_count = 0
        self.ok_count = 0
        self.waf_count = 0
        self.err_count = 0
        self.tmo_count = 0
        self.total_latency = 0.0
        
        return frame
