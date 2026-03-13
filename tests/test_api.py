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

    # Simulate a power-state notification from device
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
