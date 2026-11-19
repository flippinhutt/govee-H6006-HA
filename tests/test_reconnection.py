import asyncio
import time
from unittest.mock import AsyncMock, call, patch

import pytest

from custom_components.govee_h6006.api import GoveeAPI
from custom_components.govee_h6006.const import (
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_BACKOFF_BASE,
    RECONNECT_BACKOFF_MAX,
)


@pytest.fixture
def update_callback():
    return AsyncMock()


@pytest.fixture
def api(mock_ble_device, update_callback):
    return GoveeAPI(mock_ble_device, update_callback, model_type="H6006")


@pytest.mark.asyncio
async def test_successful_reconnection_on_first_attempt(api, mock_bleak_client):
    """Test that a successful reconnection on first attempt resets state."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        # Simulate disconnection
        api._client = None
        api._reconnect_attempts = 0

        # Attempt reconnection
        success = await api._retry_connection()

        assert success is True
        assert api._reconnect_attempts == 0
        assert api._last_disconnect_time is None
        mock_connect.assert_called_once()
        mock_bleak_client.start_notify.assert_called_once()


@pytest.mark.asyncio
async def test_exponential_backoff_timing(api, mock_bleak_client):
    """Test that exponential backoff follows the pattern: 1s, 2s, 4s, 8s."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep") as mock_sleep:
        # First 3 attempts fail, 4th succeeds
        mock_connect.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            Exception("Connection failed"),
            mock_bleak_client
        ]

        success = await api._retry_connection()

        assert success is True
        # Should sleep 1s, 2s, 4s before attempts 2, 3, 4 (no sleep before attempt 1)
        expected_sleeps = [
            call(RECONNECT_BACKOFF_BASE * 1),  # 1s before attempt 2
            call(RECONNECT_BACKOFF_BASE * 2),  # 2s before attempt 3
            call(RECONNECT_BACKOFF_BASE * 4),  # 4s before attempt 4
        ]
        assert mock_sleep.call_args_list == expected_sleeps


@pytest.mark.asyncio
async def test_backoff_capped_at_max(api, mock_bleak_client):
    """Test that backoff is capped at RECONNECT_BACKOFF_MAX (30s)."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep") as mock_sleep:
        # All attempts fail
        mock_connect.side_effect = Exception("Connection failed")

        success = await api._retry_connection()

        assert success is False
        # Check that no sleep exceeds the max
        for call_args in mock_sleep.call_args_list:
            sleep_duration = call_args[0][0]
            assert sleep_duration <= RECONNECT_BACKOFF_MAX


@pytest.mark.asyncio
async def test_max_reconnect_attempts_exceeded(api, mock_bleak_client):
    """Test that reconnection fails after MAX_RECONNECT_ATTEMPTS."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        # All attempts fail
        mock_connect.side_effect = Exception("Connection failed")

        success = await api._retry_connection()

        assert success is False
        assert api._reconnect_attempts == MAX_RECONNECT_ATTEMPTS
        assert api.is_available is False


@pytest.mark.asyncio
async def test_is_available_when_connected(api, mock_bleak_client):
    """Test is_available returns True when client is connected."""
    mock_bleak_client.is_connected = True
    api._client = mock_bleak_client
    api._reconnect_attempts = 0

    assert api.is_available is True


@pytest.mark.asyncio
async def test_is_available_when_under_max_attempts(api):
    """Test is_available returns True when reconnect attempts < max."""
    api._client = None
    api._reconnect_attempts = 3  # Less than MAX_RECONNECT_ATTEMPTS (5)

    assert api.is_available is True


@pytest.mark.asyncio
async def test_is_available_when_max_attempts_exceeded(api):
    """Test is_available returns False when max attempts exceeded."""
    api._client = None
    api._reconnect_attempts = MAX_RECONNECT_ATTEMPTS

    assert api.is_available is False


@pytest.mark.asyncio
async def test_concurrent_reconnection_prevented(api, mock_bleak_client):
    """Test that concurrent reconnection attempts are prevented by lock."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        # First call takes time to complete
        async def slow_connect(*args, **kwargs):
            await asyncio.sleep(0.1)
            return mock_bleak_client

        mock_connect.side_effect = slow_connect

        # Start first reconnection attempt
        task1 = asyncio.create_task(api._retry_connection())
        # Give it a moment to acquire the lock
        await asyncio.sleep(0.01)

        # Start second reconnection attempt (should succeed because it waits for the first)
        task2 = asyncio.create_task(api._retry_connection())

        result1 = await task1
        result2 = await task2

        assert result1 is True  # First attempt succeeds
        assert result2 is True  # Second attempt also succeeds (waited for first)
        # establish_connection should only be called once
        assert mock_connect.call_count == 1


@pytest.mark.asyncio
async def test_reconnect_counter_reset_on_success(api, mock_bleak_client):
    """Test that reconnect counter resets to 0 after successful reconnection."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        # First attempt fails, second succeeds
        mock_connect.side_effect = [
            Exception("Connection failed"),
            mock_bleak_client
        ]

        api._reconnect_attempts = 0
        success = await api._retry_connection()

        assert success is True
        assert api._reconnect_attempts == 0
        assert api._last_disconnect_time is None


@pytest.mark.asyncio
async def test_ensure_connected_raises_on_failure(api):
    """Test that _ensure_connected raises ConnectionError after max attempts."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            await api._ensure_connected()

        assert f"Failed to connect to {api.address}" in str(exc_info.value)
        assert f"after {MAX_RECONNECT_ATTEMPTS} attempts" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ensure_connected_skips_when_already_connected(api, mock_bleak_client):
    """Test that _ensure_connected skips reconnection when already connected."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect:
        mock_bleak_client.is_connected = True
        api._client = mock_bleak_client

        await api._ensure_connected()

        # Should not attempt reconnection
        mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_set_power_triggers_reconnection(api, mock_bleak_client):
    """Test that set_power triggers reconnection when disconnected."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        api._client = None

        await api.set_power(True)

        # Should have reconnected and written
        mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_poll_state_triggers_reconnection(api, mock_bleak_client):
    """Test that poll_state triggers reconnection when disconnected."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        api._client = None

        await api.poll_state()

        # Should have reconnected and written 3 query commands (power, brightness, color)
        assert mock_bleak_client.write_gatt_char.call_count == 3


@pytest.mark.asyncio
async def test_reconnection_logs_debug_messages(api, mock_bleak_client, caplog):
    """Test that reconnection attempts are logged at debug level."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        import logging
        caplog.set_level(logging.DEBUG)

        # First attempt fails, second succeeds
        mock_connect.side_effect = [
            Exception("Connection failed"),
            mock_bleak_client
        ]

        await api._retry_connection()

        # Check that debug logs were created
        log_messages = [record.message for record in caplog.records]
        assert any("Reconnection attempt" in msg for msg in log_messages)
        assert any("Reconnection successful" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_max_attempts_logs_warning(api, caplog):
    """Test that exceeding max attempts logs a warning."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect, \
         patch("asyncio.sleep"):
        import logging
        caplog.set_level(logging.DEBUG)

        # All attempts fail
        mock_connect.side_effect = Exception("Connection failed")

        await api._retry_connection()

        # Check for warning message
        warning_messages = [record.message for record in caplog.records
                           if record.levelname == "WARNING"]
        assert any("Max reconnection attempts" in msg and "marking unavailable" in msg
                  for msg in warning_messages)


@pytest.mark.asyncio
async def test_cooldown_resets_reconnection_counter(mock_ble_device):
    """Test that device becomes available again after cooldown period."""
    api = GoveeAPI(mock_ble_device, AsyncMock(), model_type="H6006")

    # Simulate 5 failed reconnection attempts
    api._reconnect_attempts = 5
    api._last_disconnect_time = time.time() - 100  # 100 seconds ago

    # Device should be unavailable (cooldown not elapsed - 100s < 300s)
    assert api.is_available is False

    # Fast-forward time past cooldown period (5 minutes = 300 seconds)
    api._last_disconnect_time = time.time() - 301  # 301 seconds ago

    # Device should now be available (cooldown elapsed)
    assert api.is_available is True

    # Counter should ONLY be reset after calling _retry_connection
    with patch("custom_components.govee_h6006.api.establish_connection", return_value=AsyncMock()):
        await api._retry_connection()

    # Now counter should be reset
    assert api._reconnect_attempts == 0
    assert api._last_disconnect_time is None
