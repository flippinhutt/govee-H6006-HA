import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.govee_h6006.coordinator import GoveeCoordinator
from custom_components.govee_h6006.const import DEFAULT_POLLING_INTERVAL


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


@pytest.fixture
def mock_hass():
    hass = MagicMock(spec=HomeAssistant)
    return hass


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


def test_coordinator_uses_default_polling_interval_when_not_in_options(mock_hass, config_entry, mock_ble_device):
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
