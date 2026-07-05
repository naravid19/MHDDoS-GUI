# tests/test_api_ws_sync.py
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_api_start_attack_passes_log_callback():
    with patch("api.worker_service.start_attack", new_callable=AsyncMock) as mock_start:
        response = client.post("/api/attack/start", json={
            "target": "https://example.com",
            "duration": 60,
            "threads": 10,
            "method": "GET",
            "rpc": 100
        })
        assert response.status_code == 200
        # Ensure log_callback was passed as a keyword argument
        assert mock_start.call_args.kwargs.get("log_callback") is not None
