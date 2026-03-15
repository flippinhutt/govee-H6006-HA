from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.govee_h6006.coordinator import GoveeCoordinator


@pytest.fixture
def config_entry():
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "ihoment_H6006",
    }
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
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        data = await coordinator._async_update_data()

        assert data.state is True
        assert data.brightness == 200
        assert data.color_rgb == (255, 0, 0)


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
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        await coordinator.set_power(True)
        api_instance.set_power.assert_called_once_with(True)
