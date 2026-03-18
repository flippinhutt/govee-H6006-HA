import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from custom_components.govee_h6006.api import GoveeAPI

@pytest.mark.asyncio
async def test_concurrent_ensure_connected_failure(mock_ble_device):
    """
    Test that concurrent calls to _ensure_connected cause one to fail incorrectly.
    This reproduces the bug where _retry_connection returns False when already
    reconnecting, causing _ensure_connected to raise ConnectionError.
    """
    update_callback = AsyncMock()
    api = GoveeAPI(mock_ble_device, update_callback)
    
    # Mock establish_connection to be slow so we can trigger concurrency
    async def slow_connect(*args, **kwargs):
        await asyncio.sleep(0.1)
        mock_client = AsyncMock()
        mock_client.is_connected = True
        return mock_client

    with patch("custom_components.govee_h6006.api.establish_connection", side_effect=slow_connect):
        # Trigger two concurrent calls to _ensure_connected (via set_power)
        results = await asyncio.gather(
            api.set_power(True),
            api.set_power(False),
            return_exceptions=True
        )
        
        # Check that both tasks succeeded
        for i, res in enumerate(results):
            assert not isinstance(res, Exception), f"Task {i} failed unexpectedly with: {res}"
        
        print("\nVerified: Concurrent calls both succeeded!")
