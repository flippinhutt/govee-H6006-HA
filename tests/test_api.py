from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.govee_h6006.api import GoveeAPI
from custom_components.govee_h6006.protocols.h6006 import H6006Protocol


@pytest.fixture
def update_callback():
    return AsyncMock()


@pytest.fixture
def api(mock_ble_device, update_callback):
    return GoveeAPI(mock_ble_device, update_callback, model_type="H6006")


@pytest.mark.asyncio
async def test_send_connects_before_transmitting(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_send_reuses_existing_connection(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        await api.set_power(False)
        # establish_connection called only once — reuses connection
        assert mock_connect.call_count == 1
        assert mock_bleak_client.write_gatt_char.call_count == 2


@pytest.mark.asyncio
async def test_set_power_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_power(True)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[0] == 0x33
        assert packet[1] == 0x01
        assert packet[2] == 0x01


@pytest.mark.asyncio
async def test_set_brightness_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_brightness(200)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x04
        assert packet[2] == 200


@pytest.mark.asyncio
async def test_set_rgb_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_color_rgb(255, 100, 50)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x05
        assert packet[3] == 255
        assert packet[4] == 100
        assert packet[5] == 50


@pytest.mark.asyncio
async def test_set_color_temp_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_color_temp(2700)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x05
        assert packet[6] == 0x01   # white sub-mode
        assert packet[7] == 255    # warm max at 2700K


@pytest.mark.asyncio
async def test_notification_updates_state(api, mock_bleak_client, update_callback):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_power(True)

    # Simulate a power-state notification from device (clear suppression to simulate real timing)
    api._suppress_update_until = 0.0
    power_on_response = bytearray(H6006Protocol.power(True))
    power_on_response[0] = 0xAA  # REQUEST head = device response
    # Recalculate checksum
    xor = 0
    for b in power_on_response[:19]:
        xor ^= b
    power_on_response[19] = xor

    await api._handle_notification(None, power_on_response)
    assert api.state is True
    update_callback.assert_called_once()


@pytest.mark.asyncio
async def test_api_passes_timeout_to_establish_connection(
    mock_ble_device, update_callback, mock_bleak_client
):
    api = GoveeAPI(
        mock_ble_device, update_callback, timeout=20.0, max_attempts=3, model_type="H6006"
    )
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        # Verify timeout and max_attempts are passed to establish_connection
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["max_attempts"] == 3
        assert call_kwargs["ble_device_callback_timeout"] == 20.0


@pytest.mark.asyncio
async def test_api_uses_default_timeout_and_retries(
    mock_ble_device, update_callback, mock_bleak_client
):
    api = GoveeAPI(mock_ble_device, update_callback, model_type="H6006")
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        # Verify default timeout and max_attempts are used
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["max_attempts"] == 5
        assert call_kwargs["ble_device_callback_timeout"] == 20.0


@pytest.mark.asyncio
async def test_reconnect_resets_state_on_success(api, mock_bleak_client):
    """Test that successful reconnection resets reconnect counter."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client), \
         patch("asyncio.sleep"):
        # Simulate a previous failed reconnection attempt
        api._reconnect_attempts = 2

        # Disconnect
        api._client = None
        mock_bleak_client.is_connected = False

        # Operation should reconnect and reset counter
        await api.set_power(False)

        # Counter should be reset to 0 after successful reconnection
        assert api._reconnect_attempts == 0
        assert api.is_available is True


@pytest.mark.asyncio
async def test_connection_timeout_is_20_seconds(api, mock_bleak_client):
    """Test that establish_connection is called with the configured timeout."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)

        # Verify establish_connection was called with the default timeout (20.0)
        call_args = mock_connect.call_args
        assert 'ble_device_callback_timeout' in call_args.kwargs
        assert call_args.kwargs['ble_device_callback_timeout'] == 20.0


@pytest.mark.asyncio
async def test_api_suppresses_rapid_notifications(mock_ble_device):
    """Test that rapid notifications are throttled based on suppression_window."""
    import time

    callback_count = 0

    async def counting_callback():
        nonlocal callback_count
        callback_count += 1

    # Create API with 500ms suppression window
    api = GoveeAPI(mock_ble_device, counting_callback, suppression_window=500, model_type="H6006")

    # Simulate 3 rapid power notifications within 100ms
    for i in range(3):
        # Simulate notification (power on)
        notification_frame = bytearray([0xAA, 0x01, 0x01] + [0] * 16)
        checksum = 0
        for b in notification_frame[:19]:
            checksum ^= b
        notification_frame.append(checksum & 0xFF)

        await api._handle_notification(None, notification_frame)
        if i < 2:
            time.sleep(0.05)  # 50ms between notifications

    # Only the first notification should have triggered callback (others suppressed)
    assert callback_count == 1

    # Wait for suppression window to expire
    time.sleep(0.6)  # 600ms

    # Send another notification
    notification_frame = bytearray([0xAA, 0x01, 0x01] + [0] * 16)
    checksum = 0
    for b in notification_frame[:19]:
        checksum ^= b
    notification_frame.append(checksum & 0xFF)
    await api._handle_notification(None, notification_frame)

    # Now callback should be called again
    assert callback_count == 2


# ========================================
# BLE Write Failures and Disconnection
# ========================================

@pytest.mark.asyncio
async def test_write_gatt_char_failure_propagates(api, mock_bleak_client):
    """Test that write_gatt_char failures propagate as exceptions."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Make write_gatt_char fail
        mock_bleak_client.write_gatt_char.side_effect = Exception("BLE write failed")

        with pytest.raises(Exception) as exc_info:
            await api.set_power(True)

        assert "BLE write failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_disconnection_during_write(api, mock_bleak_client):
    """Test that disconnection during write is detected and handled."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # First write succeeds
        await api.set_power(True)

        # Simulate disconnection
        mock_bleak_client.is_connected = False

        # Second write should reconnect
        mock_bleak_client.is_connected = True  # Reconnect succeeds
        await api.set_power(False)

        # write_gatt_char should be called twice (one for each command)
        assert mock_bleak_client.write_gatt_char.call_count == 2


@pytest.mark.asyncio
async def test_poll_state_with_max_attempts_override(api, mock_bleak_client):
    """Test that poll_state respects the max_attempts override."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               side_effect=Exception("Connection failed")) as mock_connect:
        with patch("asyncio.sleep"):
            with pytest.raises(ConnectionError):
                await api.poll_state(max_attempts=2)

        # Should have called establish_connection twice (initial + 1 retry)
        assert mock_connect.call_count == 2


@pytest.mark.asyncio
async def test_ensure_connected_failure_on_write(api, mock_bleak_client):
    """Test that connection failures during write are propagated after retries."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect:
        # Make establish_connection fail
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            await api.set_power(True)

        # After max retry attempts, a ConnectionError is raised
        assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_poll_state_write_failure(api, mock_bleak_client):
    """Test that poll_state handles write failures correctly."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Make write_gatt_char fail on second call (brightness poll)
        mock_bleak_client.write_gatt_char.side_effect = [
            None,  # Power poll succeeds
            Exception("BLE write failed"),  # Brightness poll fails
        ]

        with pytest.raises(Exception) as exc_info:
            await api.poll_state()

        assert "BLE write failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_write_after_disconnection_reconnects(api, mock_bleak_client):
    """Test that write after disconnection triggers reconnection."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        # First write establishes connection
        await api.set_power(True)
        assert mock_connect.call_count == 1

        # Simulate disconnection by clearing client
        api._client = None

        # Second write should reconnect
        await api.set_power(False)
        assert mock_connect.call_count == 2


@pytest.mark.asyncio
async def test_reconnect_cleans_up_on_notify_failure(api, mock_bleak_client):
    """Test that reconnection cleans up the client if start_notify fails."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect, \
         patch("asyncio.sleep"):

        # Make start_notify fail
        mock_bleak_client.start_notify.side_effect = Exception("Notify failed")

        # Attempting an operation should try to connect, fail at notify, and clean up
        with pytest.raises(ConnectionError):
            await api.set_power(True)

        # Should have attempted MAX_RECONNECT_ATTEMPTS (5)
        from custom_components.govee_h6006.const import MAX_RECONNECT_ATTEMPTS
        assert mock_connect.call_count == MAX_RECONNECT_ATTEMPTS

        # Verify cleanup: api._client should be None
        assert api._client is None

        # Verify disconnect was called on each failed attempt
        assert mock_bleak_client.disconnect.call_count == MAX_RECONNECT_ATTEMPTS


@pytest.mark.asyncio
async def test_multiple_write_failures(api, mock_bleak_client):
    """Test that multiple consecutive write failures are handled."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        mock_bleak_client.write_gatt_char.side_effect = Exception("BLE write failed")

        # First write fails
        with pytest.raises(Exception):
            await api.set_power(True)

        # Second write also fails
        with pytest.raises(Exception):
            await api.set_brightness(100)

        # Third write also fails
        with pytest.raises(Exception):
            await api.set_color_rgb(255, 0, 0)


@pytest.mark.asyncio
async def test_connection_established_but_disconnects_before_write(api, mock_bleak_client):
    """Test handling when connection succeeds but disconnects before write."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Connection succeeds initially
        mock_bleak_client.is_connected = True
        await api._ensure_connected()

        # Simulate disconnection before write
        mock_bleak_client.is_connected = False

        # Write should detect disconnection and reconnect
        mock_bleak_client.is_connected = True  # Reconnection succeeds
        await api.set_power(True)

        mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_set_brightness_write_failure(api, mock_bleak_client):
    """Test that set_brightness handles write failures."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        mock_bleak_client.write_gatt_char.side_effect = Exception("Write failed")

        with pytest.raises(Exception) as exc_info:
            await api.set_brightness(200)

        assert "Write failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_set_color_rgb_write_failure(api, mock_bleak_client):
    """Test that set_color_rgb handles write failures."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        mock_bleak_client.write_gatt_char.side_effect = Exception("Write failed")

        with pytest.raises(Exception) as exc_info:
            await api.set_color_rgb(255, 100, 50)

        assert "Write failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_set_color_temp_write_failure(api, mock_bleak_client):
    """Test that set_color_temp handles write failures."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        mock_bleak_client.write_gatt_char.side_effect = Exception("Write failed")

        with pytest.raises(Exception) as exc_info:
            await api.set_color_temp(3500)

        assert "Write failed" in str(exc_info.value)


# ========================================
# Notification Error Handling
# ========================================

@pytest.mark.asyncio
async def test_notification_bad_checksum(api, update_callback):
    """Test that notifications with bad checksums are discarded."""
    # Clear suppression to ensure notification would normally be processed
    api._suppress_update_until = 0.0

    # Create a notification with intentionally bad checksum
    bad_packet = bytearray([0xAA, 0x01, 0x01] + [0] * 16)
    bad_packet.append(0xFF)  # Wrong checksum (should be XOR of first 19 bytes)

    await api._handle_notification(None, bad_packet)

    # State should not be updated
    assert api.state is None
    # Callback should not be called
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_too_short(api, update_callback):
    """Test that notifications shorter than 20 bytes are discarded."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a packet that's too short (only 15 bytes)
    short_packet = bytearray([0xAA, 0x01, 0x01] + [0] * 12)

    await api._handle_notification(None, short_packet)

    # State should not be updated
    assert api.state is None
    # Callback should not be called
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_wrong_head(api, update_callback):
    """Test that notifications with wrong head byte are discarded."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a valid packet but with wrong head (0x33 instead of 0xAA)
    wrong_head_packet = bytearray([0x33, 0x01, 0x01] + [0] * 16)
    checksum = 0
    for b in wrong_head_packet[:19]:
        checksum ^= b
    wrong_head_packet.append(checksum & 0xFF)

    await api._handle_notification(None, wrong_head_packet)

    # State should not be updated
    assert api.state is None
    # Callback should not be called
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_empty_packet(api, update_callback):
    """Test that empty notifications are handled gracefully."""
    # Clear suppression
    api._suppress_update_until = 0.0

    empty_packet = bytearray()

    await api._handle_notification(None, empty_packet)

    # State should not be updated
    assert api.state is None
    # Callback should not be called
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_exactly_19_bytes(api, update_callback):
    """Test that notifications with exactly 19 bytes (missing checksum) are discarded."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a packet that's exactly 19 bytes (missing the checksum byte)
    incomplete_packet = bytearray([0xAA, 0x01, 0x01] + [0] * 16)

    await api._handle_notification(None, incomplete_packet)

    # State should not be updated
    assert api.state is None
    # Callback should not be called
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_unknown_command(api, update_callback):
    """Test that notifications with unknown command codes are handled."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a valid packet with unknown command (0x99)
    unknown_cmd_packet = bytearray([0xAA, 0x99, 0x01] + [0] * 16)
    checksum = 0
    for b in unknown_cmd_packet[:19]:
        checksum ^= b
    unknown_cmd_packet.append(checksum & 0xFF)

    await api._handle_notification(None, unknown_cmd_packet)

    # Callback should still be called (packet is valid, just unknown command)
    update_callback.assert_called_once()


@pytest.mark.asyncio
async def test_notification_all_zeros(api, update_callback):
    """Test that a packet of all zeros is handled correctly."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a packet of all zeros (checksum will also be 0)
    zero_packet = bytearray([0] * 20)

    await api._handle_notification(None, zero_packet)

    # Wrong head (0 instead of 0xAA), so should be discarded
    assert api.state is None
    update_callback.assert_not_called()


@pytest.mark.asyncio
async def test_notification_checksum_off_by_one(api, update_callback):
    """Test that a checksum off by one is detected."""
    # Clear suppression
    api._suppress_update_until = 0.0

    # Create a valid notification frame
    power_on_packet = bytearray([0xAA, 0x01, 0x01] + [0] * 16)
    checksum = 0
    for b in power_on_packet[:19]:
        checksum ^= b
    # Add checksum but make it off by one
    power_on_packet.append((checksum + 1) & 0xFF)

    await api._handle_notification(None, power_on_packet)

    # State should not be updated due to bad checksum
    assert api.state is None
    update_callback.assert_not_called()


# ========================================
# poll_state Error Handling and Edge Cases
# ========================================

@pytest.mark.asyncio
async def test_poll_state_connection_failure(api):
    """Test that poll_state handles connection failures correctly after retries."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect:
        # Make establish_connection fail
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            await api.poll_state()

        # After max retry attempts, a ConnectionError is raised
        assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_poll_state_first_query_fails(api, mock_bleak_client):
    """Test that poll_state handles failure on first query (power)."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Make write_gatt_char fail on first call (power query)
        mock_bleak_client.write_gatt_char.side_effect = Exception("BLE write failed")

        with pytest.raises(Exception) as exc_info:
            await api.poll_state()

        assert "BLE write failed" in str(exc_info.value)
        # Should only have attempted one write before failing
        assert mock_bleak_client.write_gatt_char.call_count == 1


@pytest.mark.asyncio
async def test_poll_state_last_query_fails(api, mock_bleak_client):
    """Test that poll_state handles failure on last query (color)."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Make write_gatt_char fail on third call (color query)
        mock_bleak_client.write_gatt_char.side_effect = [
            None,  # Power query succeeds
            None,  # Brightness query succeeds
            Exception("BLE write failed"),  # Color query fails
        ]

        with pytest.raises(Exception) as exc_info:
            await api.poll_state()

        assert "BLE write failed" in str(exc_info.value)
        # Should have attempted three writes
        assert mock_bleak_client.write_gatt_char.call_count == 3


@pytest.mark.asyncio
async def test_poll_state_disconnection_during_polling(api, mock_bleak_client):
    """Test that poll_state handles disconnection during polling."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # First call succeeds, then simulate disconnection
        async def write_with_disconnect(*args, **kwargs):
            # Simulate disconnection after first write
            if mock_bleak_client.write_gatt_char.call_count >= 1:
                mock_bleak_client.is_connected = False
                raise Exception("Device disconnected")

        mock_bleak_client.write_gatt_char.side_effect = write_with_disconnect

        with pytest.raises(Exception) as exc_info:
            await api.poll_state()

        assert "Device disconnected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_poll_state_success(api, mock_bleak_client):
    """Test that poll_state successfully queries all three commands."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.poll_state()

        # Should have called write_gatt_char exactly 3 times (power, brightness, color)
        assert mock_bleak_client.write_gatt_char.call_count == 3

        # Verify the command bytes sent for each query
        calls = mock_bleak_client.write_gatt_char.call_args_list

        # First call: power query (cmd=0x01)
        power_query = calls[0][0][1]
        assert power_query[0] == 0xAA  # Query head
        assert power_query[1] == 0x01  # Power command

        # Second call: brightness query (cmd=0x04)
        brightness_query = calls[1][0][1]
        assert brightness_query[0] == 0xAA  # Query head
        assert brightness_query[1] == 0x04  # Brightness command

        # Third call: color query (cmd=0x05)
        color_query = calls[2][0][1]
        assert color_query[0] == 0xAA  # Query head
        assert color_query[1] == 0x05  # Color command


@pytest.mark.asyncio
async def test_poll_state_multiple_consecutive_failures(api, mock_bleak_client):
    """Test that multiple consecutive poll_state failures are handled."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        mock_bleak_client.write_gatt_char.side_effect = Exception("BLE write failed")

        # First poll fails
        with pytest.raises(Exception):
            await api.poll_state()

        # Second poll also fails
        with pytest.raises(Exception):
            await api.poll_state()

        # Third poll also fails
        with pytest.raises(Exception):
            await api.poll_state()

        # Should have attempted 3 writes total (one per failed poll)
        assert mock_bleak_client.write_gatt_char.call_count == 3


@pytest.mark.asyncio
async def test_poll_state_reuses_existing_connection(api, mock_bleak_client):
    """Test that poll_state reuses an existing connection."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        # First poll establishes connection
        await api.poll_state()
        assert mock_connect.call_count == 1

        # Second poll reuses connection
        await api.poll_state()
        assert mock_connect.call_count == 1  # Still only called once

        # Should have 6 total writes (3 per poll)
        assert mock_bleak_client.write_gatt_char.call_count == 6


@pytest.mark.asyncio
async def test_poll_state_after_disconnection_reconnects(api, mock_bleak_client):
    """Test that poll_state reconnects after disconnection."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        # First poll establishes connection
        await api.poll_state()
        assert mock_connect.call_count == 1

        # Simulate disconnection by clearing client
        api._client = None

        # Second poll should reconnect
        await api.poll_state()
        assert mock_connect.call_count == 2


@pytest.mark.asyncio
async def test_poll_state_timeout_propagates(api, mock_bleak_client):
    """Test that timeout during poll_state is handled."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        # Make write_gatt_char timeout
        mock_bleak_client.write_gatt_char.side_effect = TimeoutError("Timeout")

        with pytest.raises(TimeoutError) as exc_info:
            await api.poll_state()

        assert "Timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_poll_state_queries_all_commands(api, mock_bleak_client):
    """Test that poll_state sends query commands for power, brightness, and color."""
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.poll_state()

        # Should write 3 query commands (power, brightness, color)
        assert mock_bleak_client.write_gatt_char.call_count == 3

        # Verify each query command is built with head=0xAA
        calls = mock_bleak_client.write_gatt_char.call_args_list
        for call in calls:
            packet = call[0][1]
            assert packet[0] == 0xAA  # REQUEST head for query packets


# ========================================
# Device Info Query Tests
# ========================================

@pytest.mark.asyncio
async def test_query_device_info_reads_all_characteristics(api, mock_bleak_client):
    """Test that query_device_info reads firmware, hardware, and model number."""
    from custom_components.govee_h6006.const import (
        FIRMWARE_REVISION_UUID,
        HARDWARE_REVISION_UUID,
        MODEL_NUMBER_UUID,
    )

    # Mock successful reads
    mock_bleak_client.read_gatt_char.side_effect = [
        b"1.02.03",  # firmware version
        b"HW_V1.0",  # hardware version
        b"H6006",    # model number
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Verify all three characteristics were read
        assert mock_bleak_client.read_gatt_char.call_count == 3

        # Verify correct UUIDs were used
        calls = mock_bleak_client.read_gatt_char.call_args_list
        assert calls[0][0][0] == FIRMWARE_REVISION_UUID
        assert calls[1][0][0] == HARDWARE_REVISION_UUID
        assert calls[2][0][0] == MODEL_NUMBER_UUID

        # Verify values were decoded and stored
        assert api.firmware_version == "1.02.03"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_query_device_info_strips_whitespace(api, mock_bleak_client):
    """Test that device info values have whitespace stripped."""
    mock_bleak_client.read_gatt_char.side_effect = [
        b"  1.02.03  \n",  # firmware with whitespace
        b"\tHW_V1.0\r\n",  # hardware with tabs/newlines
        b"  H6006  ",      # model with spaces
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Verify whitespace was stripped
        assert api.firmware_version == "1.02.03"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_query_device_info_handles_missing_firmware(api, mock_bleak_client):
    """Test that missing firmware characteristic is handled gracefully."""
    # First read fails, others succeed
    mock_bleak_client.read_gatt_char.side_effect = [
        Exception("Characteristic not found"),
        b"HW_V1.0",
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Firmware should be "Unknown", others should be read
        assert api.firmware_version == "Unknown"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_query_device_info_handles_missing_hardware(api, mock_bleak_client):
    """Test that missing hardware characteristic is handled gracefully."""
    # Second read fails, others succeed
    mock_bleak_client.read_gatt_char.side_effect = [
        b"1.02.03",
        Exception("Characteristic not found"),
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Hardware should be "Unknown", others should be read
        assert api.firmware_version == "1.02.03"
        assert api.hardware_version == "Unknown"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_query_device_info_handles_missing_model(api, mock_bleak_client):
    """Test that missing model characteristic is handled gracefully."""
    # Third read fails, others succeed
    mock_bleak_client.read_gatt_char.side_effect = [
        b"1.02.03",
        b"HW_V1.0",
        Exception("Characteristic not found"),
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Model should be "Unknown", others should be read
        assert api.firmware_version == "1.02.03"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "Unknown"


@pytest.mark.asyncio
async def test_query_device_info_handles_all_missing(api, mock_bleak_client):
    """Test that all missing characteristics are handled gracefully."""
    # All reads fail
    mock_bleak_client.read_gatt_char.side_effect = [
        Exception("Characteristic not found"),
        Exception("Characteristic not found"),
        Exception("Characteristic not found"),
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # All should be "Unknown"
        assert api.firmware_version == "Unknown"
        assert api.hardware_version == "Unknown"
        assert api.model_number == "Unknown"


@pytest.mark.asyncio
async def test_query_device_info_connects_before_reading(api, mock_bleak_client):
    """Test that query_device_info establishes connection before reading."""
    mock_bleak_client.read_gatt_char.side_effect = [
        b"1.02.03",
        b"HW_V1.0",
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.query_device_info()

        # Verify connection was established
        mock_connect.assert_called_once()

        # Verify reads happened after connection
        assert mock_bleak_client.read_gatt_char.call_count == 3


@pytest.mark.asyncio
async def test_query_device_info_reuses_existing_connection(api, mock_bleak_client):
    """Test that query_device_info reuses an existing connection."""
    mock_bleak_client.read_gatt_char.side_effect = [
        b"1.02.03",
        b"HW_V1.0",
        b"H6006",
        b"1.02.03",  # Second query
        b"HW_V1.0",
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        # First query establishes connection
        await api.query_device_info()
        assert mock_connect.call_count == 1

        # Second query reuses connection
        await api.query_device_info()
        assert mock_connect.call_count == 1  # Still only called once

        # Should have 6 total reads (3 per query)
        assert mock_bleak_client.read_gatt_char.call_count == 6


@pytest.mark.asyncio
async def test_query_device_info_connection_failure(api):
    """Test that query_device_info handles connection failures correctly."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect:
        # Make establish_connection fail
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            await api.query_device_info()

        # After max retry attempts, a ConnectionError is raised
        assert "Failed to connect" in str(exc_info.value)


@pytest.mark.asyncio
async def test_query_device_info_read_timeout(api, mock_bleak_client):
    """Test that query_device_info handles read timeout."""
    # First read times out
    mock_bleak_client.read_gatt_char.side_effect = [
        TimeoutError("Read timeout"),
        b"HW_V1.0",
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Firmware should be "Unknown" due to timeout, others should succeed
        assert api.firmware_version == "Unknown"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_query_device_info_empty_values(api, mock_bleak_client):
    """Test that empty device info values are handled."""
    mock_bleak_client.read_gatt_char.side_effect = [
        b"",  # empty firmware
        b"",  # empty hardware
        b"",  # empty model
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Empty strings after stripping should be preserved
        assert api.firmware_version == ""
        assert api.hardware_version == ""
        assert api.model_number == ""


@pytest.mark.asyncio
async def test_query_device_info_decode_error(api, mock_bleak_client):
    """Test that query_device_info handles UTF-8 decode errors."""
    # Mock invalid UTF-8 bytes
    mock_bleak_client.read_gatt_char.side_effect = [
        b"\xff\xfe\xfd",  # invalid UTF-8
        b"HW_V1.0",
        b"H6006",
    ]

    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.query_device_info()

        # Firmware should be "Unknown" due to decode error, others should succeed
        assert api.firmware_version == "Unknown"
        assert api.hardware_version == "HW_V1.0"
        assert api.model_number == "H6006"


@pytest.mark.asyncio
async def test_connect_succeeds_when_ble_device_has_no_rssi_attribute(
    mock_bleak_client, update_callback
):
    """BLEDevice.rssi was removed in newer bleak versions.
    Connection should succeed and rssi should be None, not crash."""
    device = MagicMock(spec=["address", "name"])  # no rssi attribute
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "ihoment_H6006"

    api = GoveeAPI(device, update_callback, model_type="H6006")

    with patch(
        "custom_components.govee_h6006.api.establish_connection",
        return_value=mock_bleak_client,
    ):
        await api.set_power(True)  # should not raise

    assert mock_bleak_client.write_gatt_char.called
    assert api.rssi is None
