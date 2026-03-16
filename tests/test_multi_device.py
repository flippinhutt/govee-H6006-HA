"""Tests for concurrent operation of multiple Govee H6006 coordinators."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.govee_h6006.const import DOMAIN
from custom_components.govee_h6006.coordinator import GoveeCoordinator


@pytest.fixture
def mock_hass():
    """Fixture for a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_ble_device_1():
    """Fixture for first BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:01"
    device.name = "ihoment_H6006_1"
    return device


@pytest.fixture
def mock_ble_device_2():
    """Fixture for second BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:02"
    device.name = "ihoment_H6006_2"
    return device


@pytest.fixture
def mock_ble_device_3():
    """Fixture for third BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:03"
    device.name = "ihoment_H6006_3"
    return device


@pytest.fixture
def config_entry_1():
    """Fixture for first config entry."""
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:01",
        "name": "ihoment_H6006_1",
    }
    entry.options = {}
    entry.unique_id = "AA:BB:CC:DD:EE:01"
    entry.entry_id = "entry_1"
    return entry


@pytest.fixture
def config_entry_2():
    """Fixture for second config entry."""
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:02",
        "name": "ihoment_H6006_2",
    }
    entry.options = {}
    entry.unique_id = "AA:BB:CC:DD:EE:02"
    entry.entry_id = "entry_2"
    return entry


@pytest.fixture
def config_entry_3():
    """Fixture for third config entry."""
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:03",
        "name": "ihoment_H6006_3",
    }
    entry.options = {}
    entry.unique_id = "AA:BB:CC:DD:EE:03"
    entry.entry_id = "entry_3"
    return entry


@pytest.mark.asyncio
async def test_two_coordinators_operate_independently(
    mock_hass, config_entry_1, config_entry_2, mock_ble_device_1, mock_ble_device_2
):
    """Test that two coordinators can be created and operate independently."""
    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create two separate API instances
        api_instance_1 = AsyncMock()
        api_instance_1.state = True
        api_instance_1.brightness = 100
        api_instance_1.color_rgb = (255, 0, 0)
        api_instance_1.color_temp = None
        api_instance_1.rssi = -65
        api_instance_1.connection_success_rate = 90.0
        api_instance_1.last_poll_time = 1234567890.0
        api_instance_1.connection_state = "connected"
        api_instance_1.total_reconnections = 0
        api_instance_1.update_device = MagicMock()

        api_instance_2 = AsyncMock()
        api_instance_2.state = False
        api_instance_2.brightness = 200
        api_instance_2.color_rgb = (0, 255, 0)
        api_instance_2.color_temp = None
        api_instance_2.rssi = -70
        api_instance_2.connection_success_rate = 85.0
        api_instance_2.last_poll_time = 1234567891.0
        api_instance_2.connection_state = "connected"
        api_instance_2.total_reconnections = 1
        api_instance_2.update_device = MagicMock()

        # Return different instances based on device address
        MockAPI.side_effect = lambda device, *args, **kwargs: (
            api_instance_1 if device.address == "AA:BB:CC:DD:EE:01" else api_instance_2
        )

        # Create two coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)

        # Poll both coordinators
        data_1 = await coordinator_1._async_update_data()
        data_2 = await coordinator_2._async_update_data()

        # Verify each coordinator has its own distinct state
        assert data_1.state is True
        assert data_1.brightness == 100
        assert data_1.color_rgb == (255, 0, 0)
        assert data_1.rssi == -65

        assert data_2.state is False
        assert data_2.brightness == 200
        assert data_2.color_rgb == (0, 255, 0)
        assert data_2.rssi == -70


@pytest.mark.asyncio
async def test_three_coordinators_operate_independently(
    mock_hass,
    config_entry_1,
    config_entry_2,
    config_entry_3,
    mock_ble_device_1,
    mock_ble_device_2,
    mock_ble_device_3,
):
    """Test that three coordinators can be created and operate independently."""
    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        elif address == "AA:BB:CC:DD:EE:03":
            return mock_ble_device_3
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create three separate API instances
        api_instances = []
        for i in range(3):
            api = AsyncMock()
            api.state = bool(i % 2)  # Alternate True/False
            api.brightness = 100 * (i + 1)
            api.color_rgb = (255 if i == 0 else 0, 255 if i == 1 else 0, 255 if i == 2 else 0)
            api.color_temp = None
            api.rssi = -65 - (i * 5)
            api.connection_success_rate = 90.0 - (i * 5)
            api.last_poll_time = 1234567890.0 + i
            api.connection_state = "connected"
            api.total_reconnections = i
            api.update_device = MagicMock()
            api_instances.append(api)

        # Return different instances based on device address
        def get_api_instance(device, *args, **kwargs):
            if device.address == "AA:BB:CC:DD:EE:01":
                return api_instances[0]
            elif device.address == "AA:BB:CC:DD:EE:02":
                return api_instances[1]
            else:
                return api_instances[2]

        MockAPI.side_effect = get_api_instance

        # Create three coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)
        coordinator_3 = GoveeCoordinator(mock_hass, config_entry_3)

        # Poll all coordinators
        data_1 = await coordinator_1._async_update_data()
        data_2 = await coordinator_2._async_update_data()
        data_3 = await coordinator_3._async_update_data()

        # Verify each coordinator has distinct state
        assert data_1.state is False
        assert data_1.brightness == 100
        assert data_1.color_rgb == (255, 0, 0)

        assert data_2.state is True
        assert data_2.brightness == 200
        assert data_2.color_rgb == (0, 255, 0)

        assert data_3.state is False
        assert data_3.brightness == 300
        assert data_3.color_rgb == (0, 0, 255)


@pytest.mark.asyncio
async def test_command_to_one_coordinator_does_not_affect_others(
    mock_hass, config_entry_1, config_entry_2, mock_ble_device_1, mock_ble_device_2
):
    """Test that sending commands to one coordinator doesn't affect others."""
    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create two separate API instances
        api_instance_1 = AsyncMock()
        api_instance_1.state = True
        api_instance_1.brightness = 100
        api_instance_1.color_rgb = None
        api_instance_1.color_temp = None
        api_instance_1.rssi = None
        api_instance_1.connection_success_rate = None
        api_instance_1.last_poll_time = None
        api_instance_1.connection_state = "connected"
        api_instance_1.total_reconnections = 0

        api_instance_2 = AsyncMock()
        api_instance_2.state = False
        api_instance_2.brightness = 200
        api_instance_2.color_rgb = None
        api_instance_2.color_temp = None
        api_instance_2.rssi = None
        api_instance_2.connection_success_rate = None
        api_instance_2.last_poll_time = None
        api_instance_2.connection_state = "connected"
        api_instance_2.total_reconnections = 0

        MockAPI.side_effect = lambda device, *args, **kwargs: (
            api_instance_1 if device.address == "AA:BB:CC:DD:EE:01" else api_instance_2
        )

        # Create two coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)

        # Send power command to coordinator 1
        await coordinator_1.set_power(False)

        # Verify only API 1 was called
        api_instance_1.set_power.assert_called_once_with(False)
        api_instance_2.set_power.assert_not_called()

        # Verify coordinator 1 state changed, but coordinator 2 did not
        assert coordinator_1.data.state is False
        assert coordinator_2.data.state is False  # Still at initial value
        assert coordinator_2.data.brightness == 200  # Unchanged

        # Send brightness command to coordinator 2
        await coordinator_2.set_brightness(150)

        # Verify only API 2 was called
        api_instance_2.set_brightness.assert_called_once_with(150)
        assert api_instance_1.set_brightness.call_count == 0

        # Verify coordinator 2 state changed
        assert coordinator_2.data.brightness == 150


@pytest.mark.asyncio
async def test_concurrent_commands_to_different_coordinators(
    mock_hass, config_entry_1, config_entry_2, mock_ble_device_1, mock_ble_device_2
):
    """Test that concurrent commands to different coordinators work correctly."""
    import asyncio

    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create two separate API instances
        api_instance_1 = AsyncMock()
        api_instance_1.state = True
        api_instance_1.brightness = 100
        api_instance_1.color_rgb = None
        api_instance_1.color_temp = None
        api_instance_1.rssi = None
        api_instance_1.connection_success_rate = None
        api_instance_1.last_poll_time = None
        api_instance_1.connection_state = "connected"
        api_instance_1.total_reconnections = 0

        api_instance_2 = AsyncMock()
        api_instance_2.state = False
        api_instance_2.brightness = 200
        api_instance_2.color_rgb = None
        api_instance_2.color_temp = None
        api_instance_2.rssi = None
        api_instance_2.connection_success_rate = None
        api_instance_2.last_poll_time = None
        api_instance_2.connection_state = "connected"
        api_instance_2.total_reconnections = 0

        MockAPI.side_effect = lambda device, *args, **kwargs: (
            api_instance_1 if device.address == "AA:BB:CC:DD:EE:01" else api_instance_2
        )

        # Create two coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)

        # Send concurrent commands to both coordinators
        await asyncio.gather(
            coordinator_1.set_brightness(255),
            coordinator_2.set_brightness(128),
            coordinator_1.set_color_rgb(255, 0, 0),
            coordinator_2.set_color_rgb(0, 255, 0),
        )

        # Verify both APIs were called correctly
        api_instance_1.set_brightness.assert_called_once_with(255)
        api_instance_2.set_brightness.assert_called_once_with(128)
        api_instance_1.set_color_rgb.assert_called_once_with(255, 0, 0)
        api_instance_2.set_color_rgb.assert_called_once_with(0, 255, 0)

        # Verify final states are correct
        assert coordinator_1.data.brightness == 255
        assert coordinator_1.data.color_rgb == (255, 0, 0)
        assert coordinator_2.data.brightness == 128
        assert coordinator_2.data.color_rgb == (0, 255, 0)


@pytest.mark.asyncio
async def test_concurrent_polling_of_multiple_coordinators(
    mock_hass, config_entry_1, config_entry_2, config_entry_3,
    mock_ble_device_1, mock_ble_device_2, mock_ble_device_3
):
    """Test that multiple coordinators can poll concurrently without interference."""
    import asyncio

    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        elif address == "AA:BB:CC:DD:EE:03":
            return mock_ble_device_3
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create three separate API instances
        api_instances = []
        for i in range(3):
            api = AsyncMock()
            api.state = True
            api.brightness = 100 + (i * 50)
            api.color_rgb = (255, 128 * i, 64 * i)
            api.color_temp = None
            api.rssi = -60 - (i * 10)
            api.connection_success_rate = 95.0 - (i * 5)
            api.last_poll_time = 1234567890.0 + i
            api.connection_state = "connected"
            api.total_reconnections = i
            api.update_device = MagicMock()
            api.is_available = True
            api_instances.append(api)

        def get_api_instance(device, *args, **kwargs):
            if device.address == "AA:BB:CC:DD:EE:01":
                return api_instances[0]
            elif device.address == "AA:BB:CC:DD:EE:02":
                return api_instances[1]
            else:
                return api_instances[2]

        MockAPI.side_effect = get_api_instance

        # Create three coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)
        coordinator_3 = GoveeCoordinator(mock_hass, config_entry_3)

        # Poll all coordinators concurrently
        results = await asyncio.gather(
            coordinator_1._async_update_data(),
            coordinator_2._async_update_data(),
            coordinator_3._async_update_data(),
        )

        # Verify each coordinator returned unique data
        assert results[0].brightness == 100
        assert results[0].color_rgb == (255, 0, 0)
        assert results[0].rssi == -60

        assert results[1].brightness == 150
        assert results[1].color_rgb == (255, 128, 64)
        assert results[1].rssi == -70

        assert results[2].brightness == 200
        # Note: may exceed 255, depends on API validation
        assert results[2].color_rgb == (255, 256, 128)
        assert results[2].rssi == -80

        # Verify all API instances were polled
        api_instances[0].poll_state.assert_called_once()
        api_instances[1].poll_state.assert_called_once()
        api_instances[2].poll_state.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_coordinators_in_hass_data(
    hass, mock_ble_device_1, mock_ble_device_2
):
    """Test that multiple coordinators can be stored in hass.data without conflicts."""
    config_entry_1 = MagicMock()
    config_entry_1.data = {"address": "AA:BB:CC:DD:EE:01", "name": "ihoment_H6006_1"}
    config_entry_1.options = {}
    config_entry_1.unique_id = "AA:BB:CC:DD:EE:01"
    config_entry_1.entry_id = "entry_1"

    config_entry_2 = MagicMock()
    config_entry_2.data = {"address": "AA:BB:CC:DD:EE:02", "name": "ihoment_H6006_2"}
    config_entry_2.options = {}
    config_entry_2.unique_id = "AA:BB:CC:DD:EE:02"
    config_entry_2.entry_id = "entry_2"

    with patch(
        "custom_components.govee_h6006.__init__.GoveeCoordinator"
    ) as MockCoordinator:
        coordinator_1 = AsyncMock()
        coordinator_1.async_config_entry_first_refresh = AsyncMock()
        coordinator_2 = AsyncMock()
        coordinator_2.async_config_entry_first_refresh = AsyncMock()

        MockCoordinator.side_effect = [coordinator_1, coordinator_2]

        from custom_components.govee_h6006 import async_setup_entry

        # Set up first entry
        result_1 = await async_setup_entry(hass, config_entry_1)
        assert result_1 is True
        assert DOMAIN in hass.data
        assert "entry_1" in hass.data[DOMAIN]

        # Set up second entry
        result_2 = await async_setup_entry(hass, config_entry_2)
        assert result_2 is True
        assert "entry_2" in hass.data[DOMAIN]

        # Verify both coordinators are stored separately
        assert len(hass.data[DOMAIN]) == 2
        # Verify distinct coordinator instances (not the same object)
        assert hass.data[DOMAIN]["entry_1"] is not hass.data[DOMAIN]["entry_2"]


@pytest.mark.asyncio
async def test_optimistic_updates_isolated_between_coordinators(
    mock_hass, config_entry_1, config_entry_2, mock_ble_device_1, mock_ble_device_2
):
    """Test that optimistic updates to one coordinator don't affect others."""
    def device_from_address(hass, address, connectable=True):
        if address == "AA:BB:CC:DD:EE:01":
            return mock_ble_device_1
        elif address == "AA:BB:CC:DD:EE:02":
            return mock_ble_device_2
        return None

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        side_effect=device_from_address,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        # Create two separate API instances with initial state
        api_instance_1 = AsyncMock()
        api_instance_1.state = True
        api_instance_1.brightness = 100
        api_instance_1.color_rgb = (255, 0, 0)
        api_instance_1.color_temp = None
        api_instance_1.rssi = None
        api_instance_1.connection_success_rate = None
        api_instance_1.last_poll_time = None
        api_instance_1.connection_state = "connected"
        api_instance_1.total_reconnections = 0

        api_instance_2 = AsyncMock()
        api_instance_2.state = True
        api_instance_2.brightness = 100
        api_instance_2.color_rgb = (0, 255, 0)
        api_instance_2.color_temp = None
        api_instance_2.rssi = None
        api_instance_2.connection_success_rate = None
        api_instance_2.last_poll_time = None
        api_instance_2.connection_state = "connected"
        api_instance_2.total_reconnections = 0

        MockAPI.side_effect = lambda device, *args, **kwargs: (
            api_instance_1 if device.address == "AA:BB:CC:DD:EE:01" else api_instance_2
        )

        # Create two coordinators
        coordinator_1 = GoveeCoordinator(mock_hass, config_entry_1)
        coordinator_2 = GoveeCoordinator(mock_hass, config_entry_2)

        # Set brightness on coordinator 1 (optimistic update)
        await coordinator_1.set_brightness(200)

        # Verify coordinator 1 was updated
        assert coordinator_1.data.brightness == 200
        assert api_instance_1.brightness == 200

        # Verify coordinator 2 was NOT affected
        assert api_instance_2.brightness == 100  # Still at original value

        # Set color on coordinator 2 (optimistic update)
        await coordinator_2.set_color_rgb(0, 0, 255)

        # Verify coordinator 2 was updated
        assert coordinator_2.data.color_rgb == (0, 0, 255)
        assert api_instance_2.color_rgb == (0, 0, 255)

        # Verify coordinator 1 was NOT affected
        assert api_instance_1.color_rgb == (255, 0, 0)  # Still at original value
