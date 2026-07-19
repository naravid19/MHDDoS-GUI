import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.engine import resolve_turnstile_challenge

@pytest.mark.asyncio
async def test_resolve_turnstile_challenge_height_zero_retry():
    mock_page = AsyncMock()
    mock_page.wait_for_selector.return_value = True
    
    # Simulate height 0 on first check, then height 65 on second check
    mock_page.evaluate.side_effect = [{"height": 0}, {"height": 65}]
    
    mock_frame = MagicMock()
    mock_checkbox = AsyncMock()
    mock_frame.locator.return_value = mock_checkbox
    mock_page.frame_locator = MagicMock(return_value=mock_frame)
    
    result = await resolve_turnstile_challenge(mock_page, timeout=5000)
    
    assert result is True
    assert mock_page.evaluate.call_count == 2
    mock_checkbox.click.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_turnstile_challenge_success_first_try():
    mock_page = AsyncMock()
    mock_page.wait_for_selector.return_value = True
    mock_page.evaluate.return_value = {"height": 70}
    
    mock_frame = MagicMock()
    mock_checkbox = AsyncMock()
    mock_frame.locator.return_value = mock_checkbox
    mock_page.frame_locator = MagicMock(return_value=mock_frame)
    
    result = await resolve_turnstile_challenge(mock_page, timeout=5000)
    
    assert result is True
    assert mock_page.evaluate.call_count == 1
    mock_checkbox.click.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_turnstile_challenge_always_zero_height_fails():
    mock_page = AsyncMock()
    mock_page.wait_for_selector.return_value = True
    mock_page.evaluate.return_value = {"height": 0}
    
    mock_frame = MagicMock()
    mock_checkbox = AsyncMock()
    mock_frame.locator.return_value = mock_checkbox
    mock_page.frame_locator = MagicMock(return_value=mock_frame)
    
    result = await resolve_turnstile_challenge(mock_page, timeout=5000)
    
    assert result is False
    assert mock_page.evaluate.call_count == 5
    mock_checkbox.click.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_turnstile_challenge_element_not_found_fails():
    mock_page = AsyncMock()
    mock_page.wait_for_selector.side_effect = Exception("Selector timeout")
    
    result = await resolve_turnstile_challenge(mock_page, timeout=5000)
    
    assert result is False
