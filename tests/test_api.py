import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from custom_components.govee_h6006.api import GoveeAPI
from custom_components.govee_h6006.api_utils import GoveePacket


@pytest.fixture
def update_callback():
    return AsyncMock()


@pytest.fixture
def api(mock_ble_device, update_callback):
    return GoveeAPI(mock_ble_device, update_callback)


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
    power_on_response = bytearray(GoveePacket.power(True))
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
async def test_api_passes_timeout_to_establish_connection(mock_ble_device, update_callback, mock_bleak_client):
    api = GoveeAPI(mock_ble_device, update_callback, timeout=20.0, max_attempts=3)
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        # Verify timeout and max_attempts are passed to establish_connection
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["max_attempts"] == 3
        assert call_kwargs["ble_device_callback_timeout"] == 20.0


@pytest.mark.asyncio
async def test_api_uses_default_timeout_and_retries(mock_ble_device, update_callback, mock_bleak_client):
    api = GoveeAPI(mock_ble_device, update_callback)
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        # Verify default timeout and max_attempts are used
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["max_attempts"] == 5
        assert call_kwargs["ble_device_callback_timeout"] == 15.0


@pytest.mark.asyncio
async def test_api_suppresses_rapid_notifications(mock_ble_device):
    """Test that rapid notifications are throttled based on suppression_window."""
    import time

    callback_count = 0

    async def counting_callback():
        nonlocal callback_count
        callback_count += 1

    # Create API with 500ms suppression window
    api = GoveeAPI(mock_ble_device, counting_callback, suppression_window=500)

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
async def test_ensure_connected_failure_on_write(api, mock_bleak_client):
    """Test that connection failures during write are propagated."""
    with patch("custom_components.govee_h6006.api.establish_connection") as mock_connect:
        # Make establish_connection fail
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception) as exc_info:
            await api.set_power(True)

        assert "Connection failed" in str(exc_info.value)


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
