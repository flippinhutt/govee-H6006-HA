from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.govee_h6006.const import DEFAULT_POLLING_INTERVAL
from custom_components.govee_h6006.coordinator import GoveeCoordinator


@pytest.fixture
def config_entry():
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "ihoment_H6006",
    }
    entry.options = {}
    entry.unique_id = "AA:BB:CC:DD:EE:FF"
    return entry


@pytest.mark.asyncio
async def test_coordinator_polls_device_state(mock_hass, config_entry, mock_ble_device):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None
        # Mock diagnostic fields
        api_instance.rssi = -65
        api_instance.connection_success_rate = 90.0
        api_instance.last_poll_time = 1234567890.0
        api_instance.connection_state = "connected"
        api_instance.total_reconnections = 2
        api_instance.update_device = MagicMock()  # Not async
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        data = await coordinator._async_update_data()

        assert data.state is True
        assert data.brightness == 200
        assert data.color_rgb == (255, 0, 0)
        # Verify diagnostic fields are propagated
        assert data.rssi == -65
        assert data.connection_success_rate == 90.0
        assert data.last_poll_time is not None
        assert data.connection_state == "connected"
        assert data.total_reconnections == 2


def test_coordinator_raises_when_device_not_found(mock_hass, config_entry):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        with pytest.raises(Exception):
            GoveeCoordinator(mock_hass, config_entry)


@pytest.mark.asyncio
async def test_coordinator_set_power_delegates_to_api(mock_hass, config_entry, mock_ble_device):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        # Mock diagnostic fields so _snapshot() works
        api_instance.rssi = None
        api_instance.connection_success_rate = None
        api_instance.last_poll_time = None
        api_instance.connection_state = "disconnected"
        api_instance.total_reconnections = 0
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        await coordinator.set_power(True)
        api_instance.set_power.assert_called_once_with(True)


def test_coordinator_uses_polling_interval_from_options(mock_hass, config_entry, mock_ble_device):
    """Test that coordinator uses polling interval from config_entry.options."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        MockAPI.return_value = AsyncMock()

        # Test with custom polling interval
        config_entry.options = {"polling_interval": 60}
        coordinator = GoveeCoordinator(mock_hass, config_entry)
        assert coordinator.update_interval == timedelta(seconds=60)


def test_coordinator_uses_default_polling_interval_when_not_in_options(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator uses default polling interval when not specified in options."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        MockAPI.return_value = AsyncMock()

        # Test with no options
        config_entry.options = {}
        coordinator = GoveeCoordinator(mock_hass, config_entry)
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_POLLING_INTERVAL)


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_when_device_not_found_during_update(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator raises UpdateFailed when BLE device is not found during update."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address"
    ) as mock_async_ble_device, patch(
        "custom_components.govee_h6006.coordinator.GoveeAPI"
    ) as MockAPI:
        # First call returns device (for __init__), second call returns None (for update)
        mock_async_ble_device.side_effect = [mock_ble_device, None]
        MockAPI.return_value = AsyncMock()

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        with pytest.raises(UpdateFailed, match="BLE device AA:BB:CC:DD:EE:FF not found"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_when_device_unavailable(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator raises UpdateFailed when device is unavailable."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.is_available = False
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        with pytest.raises(UpdateFailed, match="is unavailable after max reconnection attempts"):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_raises_update_failed_on_poll_state_exception(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator raises UpdateFailed when poll_state raises an exception."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.is_available = True
        api_instance.poll_state.side_effect = Exception("Connection timeout")
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        with pytest.raises(
            UpdateFailed, match="Error communicating with AA:BB:CC:DD:EE:FF: Connection timeout"
        ):
            await coordinator._async_update_data()


def test_coordinator_available_returns_true_when_api_is_available(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator.available returns True when API is available."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.is_available = True
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        assert coordinator.available is True


def test_coordinator_available_returns_false_when_api_is_unavailable(
    mock_hass, config_entry, mock_ble_device
):
    """Test that coordinator.available returns False when API is unavailable."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.is_available = False
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        assert coordinator.available is False


@pytest.mark.asyncio
async def test_coordinator_set_brightness_optimistic_update(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness performs optimistic update before calling API."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 100
        api_instance.color_rgb = None
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform optimistic update
        await coordinator.set_brightness(200)

        # Verify API brightness was updated optimistically
        assert api_instance.brightness == 200
        # Verify API method was called
        api_instance.set_brightness.assert_called_once_with(200)


@pytest.mark.asyncio
async def test_coordinator_set_color_rgb_optimistic_update(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_rgb performs optimistic update and clears color_temp."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (0, 0, 0)
        api_instance.color_temp = 4000
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform optimistic update
        await coordinator.set_color_rgb(255, 128, 64)

        # Verify API color was updated optimistically
        assert api_instance.color_rgb == (255, 128, 64)
        # Verify color_temp was cleared
        assert api_instance.color_temp is None
        # Verify API method was called
        api_instance.set_color_rgb.assert_called_once_with(255, 128, 64)


@pytest.mark.asyncio
async def test_coordinator_set_color_temp_optimistic_update(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_temp performs optimistic update and clears color_rgb."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform optimistic update
        await coordinator.set_color_temp(5000)

        # Verify API color_temp was updated optimistically
        assert api_instance.color_temp == 5000
        # Verify color_rgb was cleared
        assert api_instance.color_rgb is None
        # Verify API method was called
        api_instance.set_color_temp.assert_called_once_with(5000)


@pytest.mark.asyncio
async def test_coordinator_queries_device_info_on_init(mock_hass, config_entry, mock_ble_device):
    """Test that coordinator calls query_device_info during initialization."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.query_device_info = AsyncMock()
        mock_api_class.return_value = mock_api

        _ = GoveeCoordinator(mock_hass, config_entry)

        # Wait for any async tasks to complete
        await mock_hass.async_block_till_done()

        # Verify query_device_info was called
        mock_api.query_device_info.assert_called_once()


@pytest.mark.asyncio
async def test_coordinator_data_includes_device_info(mock_hass, config_entry, mock_ble_device):
    """Test that coordinator.data includes device info fields."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api_class:
        # Set up mock API with device info
        mock_api = AsyncMock()
        mock_api.firmware_version = "1.02.03"
        mock_api.hardware_version = "HW_V1.0"
        mock_api.model_number = "H6006"
        mock_api_class.return_value = mock_api

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        await coordinator.async_config_entry_first_refresh()

        # Verify device info is in coordinator.data
        assert coordinator.data.firmware_version == "1.02.03"
        assert coordinator.data.hardware_version == "HW_V1.0"
        assert coordinator.data.model_number == "H6006"


@pytest.mark.asyncio
async def test_firmware_version_logged_at_info_level(
    mock_hass, config_entry, mock_ble_device, caplog
):
    """Test that firmware version is logged at INFO level."""
    import logging

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api_class:
        mock_api = AsyncMock()
        mock_api.firmware_version = "1.02.03"
        mock_api.hardware_version = "HW_V1.0"
        mock_api.model_number = "H6006"
        mock_api_class.return_value = mock_api

        with caplog.at_level(logging.INFO):
            _ = GoveeCoordinator(mock_hass, config_entry)
            await mock_hass.async_block_till_done()

        # Verify INFO log contains firmware version
        assert "1.02.03" in caplog.text
        assert "Firmware" in caplog.text or "firmware" in caplog.text
