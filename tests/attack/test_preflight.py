import asyncio
import json
import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.main import start_attack, AttackParams, ReconManager, StatusResponse

@pytest.mark.asyncio
async def test_dns_preflight_failure():
    # Setup
    params = AttackParams(
        target="unresolved.invalid",
        method="GET",
        threads=10,
        duration=60
    )
    
    # Mock ReconManager.enumerate_dns to return no records
    mock_dns = {
        "status": "success",
        "domain": "unresolved.invalid",
        "records": {"A": [], "AAAA": []}
    }
    
    with patch("src.app.main.ReconManager.enumerate_dns", new_callable=AsyncMock) as mock_enum:
        mock_dns_func = mock_enum
        mock_dns_func.return_value = mock_dns
        
        # Mock fire_webhook to avoid real HTTP calls
        with patch("src.app.main.fire_webhook", new_callable=AsyncMock):
            # Mock run_attack_subprocess to ensure it's NOT called
            with patch("src.app.main.run_attack_subprocess", new_callable=AsyncMock) as mock_run:
                response = await start_attack(params)
                
                assert response.status == "error"
                assert "DNS Preflight Failed" in response.message
                mock_run.assert_not_called()

@pytest.mark.asyncio
async def test_dns_preflight_success():
    # Setup
    params = AttackParams(
        target="google.com",
        method="GET",
        threads=10,
        duration=60
    )
    
    # Mock ReconManager.enumerate_dns to return a valid record
    mock_dns = {
        "status": "success",
        "domain": "google.com",
        "records": {"A": ["1.2.3.4"]}
    }
    
    with patch("src.app.main.ReconManager.enumerate_dns", new_callable=AsyncMock) as mock_enum:
        mock_enum.return_value = mock_dns
        
        # Mock fire_webhook
        with patch("src.app.main.fire_webhook", new_callable=AsyncMock):
            # Mock run_attack_subprocess to ensure it IS called
            with patch("src.app.main.run_attack_subprocess", new_callable=AsyncMock) as mock_run:
                response = await start_attack(params)
                
                assert response.status == "success"
                assert "Attack sequence initiated" in response.message
                # Since it's created as a task, we can't easily assert_called() 
                # unless we wait or patch correctly. 
                # But our current implementation should proceed to spawn.
                assert mock_run.called

@pytest.mark.asyncio
async def test_dns_preflight_ip_and_localhost():
    # Test ReconManager.enumerate_dns directly
    res_ip = await ReconManager.enumerate_dns("http://127.0.0.1:8001")
    assert res_ip["status"] == "success"
    assert "127.0.0.1" in res_ip["records"]["A"]
    
    res_local = await ReconManager.enumerate_dns("localhost:3000")
    assert res_local["status"] == "success"
    assert "127.0.0.1" in res_local["records"]["A"]
    
    # Test start_attack with IP address
    params = AttackParams(
        target="http://127.0.0.1:8001",
        method="GET",
        threads=10,
        duration=60
    )
    with patch("src.app.main.fire_webhook", new_callable=AsyncMock):
        with patch("src.app.main.run_attack_subprocess", new_callable=AsyncMock) as mock_run:
            response = await start_attack(params)
            assert response.status == "success"
            assert mock_run.called

if __name__ == "__main__":
    asyncio.run(test_dns_preflight_failure())
    asyncio.run(test_dns_preflight_success())
    asyncio.run(test_dns_preflight_ip_and_localhost())
    print("Preflight tests PASSED.")