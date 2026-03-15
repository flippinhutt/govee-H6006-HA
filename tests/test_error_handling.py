import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
async def test_set_power_rollback_on_failure(mock_hass, config_entry, mock_ble_device):
    """Test that set_power rolls back state when API call fails."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock
        api_instance = AsyncMock()
        api_instance.state = True  # Initial state: ON
        api_instance.brightness = 200
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None
        api_instance.is_available = True

        # Make set_power raise an exception
        api_instance.set_power.side_effect = ConnectionError("BLE connection failed")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial state
        assert coordinator.data.state is True

        # Attempt to turn OFF - should fail and rollback
        with pytest.raises(HomeAssistantError) as exc_info:
            await coordinator.set_power(False)

        # Verify error message contains the underlying error
        assert "Failed to set power state" in str(exc_info.value)
        assert "BLE connection failed" in str(exc_info.value)

        # Verify API method was called with the new state
        api_instance.set_power.assert_called_once_with(False)

        # Verify state rolled back to original value (True)
        assert coordinator.data.state is True

        # Verify underlying API state also rolled back
        assert api_instance.state is True


@pytest.mark.asyncio
async def test_set_brightness_rollback_on_failure(mock_hass, config_entry, mock_ble_device):
    """Test that set_brightness rolls back state when API call fails."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 100  # Initial brightness
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None
        api_instance.is_available = True

        # Make set_brightness raise an exception
        api_instance.set_brightness.side_effect = ConnectionError("Device disconnected")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial brightness
        assert coordinator.data.brightness == 100

        # Attempt to change brightness - should fail and rollback
        with pytest.raises(HomeAssistantError) as exc_info:
            await coordinator.set_brightness(200)

        # Verify error message
        assert "Failed to set brightness" in str(exc_info.value)

        # Verify API method was called
        api_instance.set_brightness.assert_called_once_with(200)

        # Verify brightness rolled back to original value
        assert coordinator.data.brightness == 100
        assert api_instance.brightness == 100


@pytest.mark.asyncio
async def test_set_color_rgb_rollback_on_failure(mock_hass, config_entry, mock_ble_device):
    """Test that set_color_rgb rolls back state when API call fails."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = (255, 0, 0)  # Initial color: red
        api_instance.color_temp = None
        api_instance.is_available = True

        # Make set_color_rgb raise an exception
        api_instance.set_color_rgb.side_effect = TimeoutError("Command timeout")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial color
        assert coordinator.data.color_rgb == (255, 0, 0)
        assert coordinator.data.color_temp is None

        # Attempt to change color to blue - should fail and rollback
        with pytest.raises(HomeAssistantError) as exc_info:
            await coordinator.set_color_rgb(0, 0, 255)

        # Verify error message
        assert "Failed to set color RGB" in str(exc_info.value)

        # Verify API method was called
        api_instance.set_color_rgb.assert_called_once_with(0, 0, 255)

        # Verify color rolled back to original value
        assert coordinator.data.color_rgb == (255, 0, 0)
        assert coordinator.data.color_temp is None
        assert api_instance.color_rgb == (255, 0, 0)


@pytest.mark.asyncio
async def test_set_color_temp_rollback_on_failure(mock_hass, config_entry, mock_ble_device):
    """Test that set_color_temp rolls back state when API call fails."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = None
        api_instance.color_temp = 3000  # Initial color temp: warm white
        api_instance.is_available = True

        # Make set_color_temp raise an exception
        api_instance.set_color_temp.side_effect = OSError("BLE adapter error")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial color temp
        assert coordinator.data.color_temp == 3000
        assert coordinator.data.color_rgb is None

        # Attempt to change color temp to cool white - should fail and rollback
        with pytest.raises(HomeAssistantError) as exc_info:
            await coordinator.set_color_temp(6000)

        # Verify error message
        assert "Failed to set color temperature" in str(exc_info.value)

        # Verify API method was called
        api_instance.set_color_temp.assert_called_once_with(6000)

        # Verify color temp rolled back to original value
        assert coordinator.data.color_temp == 3000
        assert coordinator.data.color_rgb is None
        assert api_instance.color_temp == 3000


@pytest.mark.asyncio
async def test_set_color_rgb_rollback_preserves_color_temp(mock_hass, config_entry, mock_ble_device):
    """Test that set_color_rgb rollback restores previous color temp mode."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock in color temp mode
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = None  # Not in RGB mode
        api_instance.color_temp = 4000  # In color temp mode
        api_instance.is_available = True

        # Make set_color_rgb raise an exception
        api_instance.set_color_rgb.side_effect = Exception("Hardware fault")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial state: color temp mode
        assert coordinator.data.color_rgb is None
        assert coordinator.data.color_temp == 4000

        # Attempt to switch to RGB mode - should fail and rollback
        with pytest.raises(HomeAssistantError):
            await coordinator.set_color_rgb(128, 128, 255)

        # Verify state rolled back to color temp mode
        assert coordinator.data.color_rgb is None
        assert coordinator.data.color_temp == 4000
        assert api_instance.color_rgb is None
        assert api_instance.color_temp == 4000


@pytest.mark.asyncio
async def test_set_color_temp_rollback_preserves_rgb(mock_hass, config_entry, mock_ble_device):
    """Test that set_color_temp rollback restores previous RGB mode."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Set up API mock in RGB mode
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = (0, 255, 0)  # In RGB mode (green)
        api_instance.color_temp = None  # Not in color temp mode
        api_instance.is_available = True

        # Make set_color_temp raise an exception
        api_instance.set_color_temp.side_effect = Exception("Communication error")

        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Verify initial state: RGB mode
        assert coordinator.data.color_rgb == (0, 255, 0)
        assert coordinator.data.color_temp is None

        # Attempt to switch to color temp mode - should fail and rollback
        with pytest.raises(HomeAssistantError):
            await coordinator.set_color_temp(5000)

        # Verify state rolled back to RGB mode
        assert coordinator.data.color_rgb == (0, 255, 0)
        assert coordinator.data.color_temp is None
        assert api_instance.color_rgb == (0, 255, 0)
        assert api_instance.color_temp is None
