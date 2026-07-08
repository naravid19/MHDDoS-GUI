# src/worker/service.py
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
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
        self._process: asyncio.subprocess.Process | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._active_tasks: set[asyncio.Task[Any]] = set()

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
    ) -> None:
        async with self._lock:
            if self._process is not None and self._process.returncode is None:
                raise RuntimeError("An attack is already running.")

            cmd = cmd_args if cmd_args is not None else [
                sys.executable, "-m", "mhddos_gui.cli",
                "--target", target,
                "--duration", str(duration),
                "--threads", str(threads),
                "--method", method,
                "--rpc", str(rpc)
            ]
            logger.info(f"Starting attack process: {' '.join(cmd)}")

            try:
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
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
                attack_id=attack_id or "local-1",
                target=target,
                method=method,
            )
            await self._broadcast_state()

            self._monitor_task = asyncio.create_task(self._monitor_process(self._process, log_callback))

    async def stop_attack(self) -> None:
        async with self._lock:
            if self._process is None or self._process.returncode is not None:
                logger.warning("No running attack process to stop.")
                return

            logger.info(f"Terminating attack process tree (PID: {self._process.pid})...")
            await self._terminate_process_tree(self._process.pid)
            
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process did not exit in time after termination command.")
            
            self._process = None

            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            self._monitor_task = None

        await state_manager.update_status(AttackStatus.STOPPED)
        await self._broadcast_state()

    async def _monitor_process(self, proc: ProcessLike, log_callback: Any | None = None) -> None:
        """Monitor process stdout using buffered reading and sequential Queue-based logging."""
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def log_consumer() -> None:
            """Consume logs sequentially from queue to guarantee order."""
            while True:
                line = await queue.get()
                try:
                    if log_callback:
                        if asyncio.iscoroutinefunction(log_callback):
                            await log_callback(line)
                        else:
                            log_callback(line)
                except Exception as e:
                    logger.debug(f"Error in log_callback: {e}")
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
                            decoded = buffer.decode("utf-8", errors="replace").strip()
                            if decoded:
                                await queue.put(decoded)
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        decoded = line.decode("utf-8", errors="replace").strip()
                        if decoded:
                            await queue.put(decoded)

            # Ensure all log items are consumed before finishing
            await queue.join()

            returncode = await proc.wait()
            async with self._lock:
                if self._process is proc:
                    self._process = None
            
            if returncode == 0:
                logger.info("Attack process completed successfully.")
                await state_manager.update_status(AttackStatus.COMPLETED)
            else:
                logger.error(f"Attack process exited with unexpected code {returncode}.")
                await state_manager.update_status(AttackStatus.ERROR, f"Process exited with code {returncode}")
            
            await self._broadcast_state()
        except asyncio.CancelledError:
            logger.debug("Process monitor task cancelled.")
        except Exception as exc:
            logger.exception(f"Error monitoring attack process: {exc}")
            await state_manager.update_status(AttackStatus.ERROR, str(exc))
            await self._broadcast_state()
        finally:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

    async def _terminate_process_tree(self, target: Any) -> None:
        """Robust multi-layer process tree termination using taskkill (first on Windows), psutil, and process handles."""
        pid = None
        proc = None
        if isinstance(target, int):
            pid = target
            if self._process and getattr(self._process, "pid", None) == pid:
                proc = self._process
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
