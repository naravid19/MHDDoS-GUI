# tests/test_worker_service_buffered.py
from __future__ import annotations

import asyncio
import pytest
from src.worker.service import WorkerService, StreamReaderLike, ProcessLike


class MockStdout:
    """Mock StreamReader that feeds predefined chunks of bytes."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Initialize mock stream chunks.

        Args:
            chunks: List of byte chunks to yield sequentially.
        """
        self._chunks = chunks.copy()

    async def read(self, n: int = -1) -> bytes:
        """Read next chunk of bytes.

        Args:
            n: Number of bytes to read (ignored).

        Returns:
            The next bytes chunk or empty bytes if finished.
        """
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class MockProcess:
    """Mock process interface conforming to ProcessLike."""

    def __init__(self, stdout: MockStdout) -> None:
        """Initialize mock process.

        Args:
            stdout: The MockStdout stream.
        """
        self._stdout = stdout
        self.returncode = 0

    @property
    def stdout(self) -> StreamReaderLike | None:
        """Return the stdout stream."""
        return self._stdout

    async def wait(self) -> int:
        """Wait for process completion.

        Returns:
            The exit returncode.
        """
        return 0


@pytest.mark.asyncio
async def test_monitor_process_buffered_reading() -> None:
    """Test process stdout monitoring in chunked buffers."""
    service = WorkerService()
    logs: list[str] = []

    def callback(msg: str) -> None:
        logs.append(msg)

    stdout = MockStdout([b"Line 1\nLine ", b"2\nLine 3\n"])
    proc = MockProcess(stdout)

    await service._monitor_process(proc, callback)
    assert logs == ["Line 1", "Line 2", "Line 3"]


@pytest.mark.asyncio
async def test_monitor_process_log_ordering_and_async_callback() -> None:
    """Verify that log callback ordering is strictly preserved with async callbacks."""
    service = WorkerService()
    logs: list[str] = []

    async def async_callback(msg: str) -> None:
        # Simulate slight random sleep to check if sequential execution is maintained
        if msg == "Line 1":
            await asyncio.sleep(0.05)
        elif msg == "Line 2":
            await asyncio.sleep(0.01)
        logs.append(msg)

    # Yield many lines split randomly
    stdout = MockStdout([
        b"Line 1\n",
        b"Line 2\nLine 3\n",
        b"Line 4\nLine 5",
        b"\nLine 6\n"
    ])
    proc = MockProcess(stdout)

    await service._monitor_process(proc, async_callback)
    
    # Assert logs are dispatched strictly in order, despite differing async execution times
    assert logs == ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5", "Line 6"]
