import asyncio
import pytest
from typing import Any
from src.worker.service import WorkerService

class MockStdout:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks.copy()

    async def read(self, n: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

class MockProcess:
    def __init__(self, stdout: MockStdout) -> None:
        self.stdout = stdout
        self.returncode = 0

    async def wait(self) -> int:
        return 0

@pytest.mark.asyncio
async def test_monitor_process_buffered_reading() -> None:
    service = WorkerService()
    logs: list[str] = []

    def callback(msg: str) -> None:
        logs.append(msg)

    stdout = MockStdout([b"Line 1\nLine ", b"2\nLine 3\n"])
    proc = MockProcess(stdout)

    await service._monitor_process(proc, callback)
    assert logs == ["Line 1", "Line 2", "Line 3"]
