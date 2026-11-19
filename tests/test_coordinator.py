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


def test_coordinator_handles_missing_device_on_init(mock_hass, config_entry):
    """Test that coordinator handles missing BLE device during initialization."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        # Should not raise RuntimeError anymore
        coordinator = GoveeCoordinator(mock_hass, config_entry)
        assert coordinator.device_address == config_entry.data["address"]


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


@pytest.mark.asyncio
async def test_coordinator_first_refresh_fast_fail(mock_hass, config_entry, mock_ble_device):
    """Test that the first refresh uses fast-fail logic (2 attempts)."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        MockAPI.return_value = api_instance

        # Initialize coordinator
        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # First refresh
        await coordinator._async_update_data()
        api_instance.poll_state.assert_called_once_with(max_attempts=2)

        # Second refresh (polling)
        api_instance.poll_state.reset_mock()
        await coordinator._async_update_data()
        api_instance.poll_state.assert_called_with(max_attempts=None)


@pytest.mark.asyncio
async def test_coordinator_init_queries_device_info_with_limit(
    mock_hass, config_entry, mock_ble_device
):
    """Test that the background device info task uses fast-fail limit during init."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        MockAPI.return_value = api_instance

        # Initialize coordinator
        # The background task is created on init
        GoveeCoordinator(mock_hass, config_entry)

        # Verify the task was created and run it
        await mock_hass.async_block_till_done()

        # Verify it was called with limit
        api_instance.query_device_info.assert_called_once_with(max_attempts=2)
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

        with pytest.raises(UpdateFailed, match="is unavailable"):
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
async def test_coordinator_set_brightness_with_transition_interpolates_values(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness_with_transition sends interpolated brightness values."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 100
        api_instance.color_rgb = None
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform transition (0.2s = 2 steps at 0.1s interval)
        await coordinator.set_brightness_with_transition(200, 0.2)

        # Verify API was called multiple times with interpolated values
        assert api_instance.set_brightness.call_count == 2
        # First call should be halfway (150)
        api_instance.set_brightness.assert_any_call(150)
        # Last call should be target (200)
        api_instance.set_brightness.assert_any_call(200)


@pytest.mark.asyncio
async def test_coordinator_set_brightness_with_transition_falls_back_to_instant_when_too_short(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness_with_transition falls back to instant change
    for very short transitions."""
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

        # Transition shorter than MIN_TRANSITION_DURATION (0.1s)
        await coordinator.set_brightness_with_transition(200, 0.05)

        # Should call set_brightness exactly once (instant change, no transition)
        api_instance.set_brightness.assert_called_once_with(200)


@pytest.mark.asyncio
async def test_coordinator_set_brightness_with_transition_falls_back_when_brightness_none(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness_with_transition falls back to instant change
    when brightness is None."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = False
        api_instance.brightness = None  # Device is off
        api_instance.color_rgb = None
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Transition with None brightness
        await coordinator.set_brightness_with_transition(200, 1.0)

        # Should call set_brightness exactly once (instant change, no transition)
        api_instance.set_brightness.assert_called_once_with(200)


@pytest.mark.asyncio
async def test_coordinator_set_brightness_with_transition_clamps_duration(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness_with_transition clamps transition duration to allowed range."""

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 100
        api_instance.color_rgb = None
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Request transition longer than MAX_TRANSITION_DURATION (300s)
        await coordinator.set_brightness_with_transition(200, 500)

        # Should have clamped to MAX_TRANSITION_DURATION (300s = 3000 steps)
        assert api_instance.set_brightness.call_count == 3000


@pytest.mark.asyncio
async def test_coordinator_set_brightness_with_transition_cancels_previous_transition(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_brightness_with_transition cancels previous transition."""
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

        # Start first transition but don't await it
        import asyncio

        task1 = asyncio.create_task(coordinator.set_brightness_with_transition(150, 0.3))

        # Give it time to start and create the internal task
        await asyncio.sleep(0.01)

        # Verify the internal transition task exists
        first_transition_task = coordinator._transition_task
        assert first_transition_task is not None

        # Start second transition (should cancel first)
        await coordinator.set_brightness_with_transition(200, 0.1)

        # First internal transition task should be cancelled
        assert first_transition_task.cancelled()

        # Clean up the first outer task
        try:
            await task1
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_coordinator_set_color_rgb_with_transition_interpolates_values(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_rgb_with_transition sends interpolated RGB values."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (0, 0, 0)
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform transition (0.2s = 2 steps at 0.1s interval)
        await coordinator.set_color_rgb_with_transition(100, 200, 50, 0.2)

        # Verify API was called multiple times with interpolated values
        assert api_instance.set_color_rgb.call_count == 2
        # First call should be halfway (50, 100, 25)
        api_instance.set_color_rgb.assert_any_call(50, 100, 25)
        # Last call should be target (100, 200, 50)
        api_instance.set_color_rgb.assert_any_call(100, 200, 50)


@pytest.mark.asyncio
async def test_coordinator_set_color_rgb_with_transition_falls_back_when_color_rgb_none(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_rgb_with_transition falls back to instant change
    when color_rgb is None."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = None  # No current color
        api_instance.color_temp = 4000
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Transition with None color_rgb
        await coordinator.set_color_rgb_with_transition(100, 200, 50, 1.0)

        # Should call set_color_rgb exactly once (instant change, no transition)
        api_instance.set_color_rgb.assert_called_once_with(100, 200, 50)


@pytest.mark.asyncio
async def test_coordinator_set_color_rgb_with_transition_clears_color_temp(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_rgb_with_transition clears color_temp during transition."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (0, 0, 0)
        api_instance.color_temp = 4000  # Has color temp set
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform transition
        await coordinator.set_color_rgb_with_transition(100, 200, 50, 0.2)

        # Verify color_temp was cleared
        assert api_instance.color_temp is None


@pytest.mark.asyncio
async def test_coordinator_set_color_temp_with_transition_interpolates_values(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_temp_with_transition sends interpolated color temp values."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = None
        api_instance.color_temp = 3000
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform transition (0.2s = 2 steps at 0.1s interval)
        await coordinator.set_color_temp_with_transition(5000, 0.2)

        # Verify API was called multiple times with interpolated values
        assert api_instance.set_color_temp.call_count == 2
        # First call should be halfway (4000)
        api_instance.set_color_temp.assert_any_call(4000)
        # Last call should be target (5000)
        api_instance.set_color_temp.assert_any_call(5000)


@pytest.mark.asyncio
async def test_coordinator_set_color_temp_with_transition_falls_back_when_color_temp_none(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_temp_with_transition falls back to instant change
    when color_temp is None."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None  # No current color temp
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Transition with None color_temp
        await coordinator.set_color_temp_with_transition(5000, 1.0)

        # Should call set_color_temp exactly once (instant change, no transition)
        api_instance.set_color_temp.assert_called_once_with(5000)


@pytest.mark.asyncio
async def test_coordinator_set_color_temp_with_transition_clears_color_rgb(
    mock_hass, config_entry, mock_ble_device
):
    """Test that set_color_temp_with_transition clears color_rgb during transition."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI, patch(
        "custom_components.govee_h6006.coordinator.asyncio.sleep"
    ):
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 255
        api_instance.color_rgb = (255, 0, 0)  # Has RGB set
        api_instance.color_temp = 3000
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Perform transition
        await coordinator.set_color_temp_with_transition(5000, 0.2)

        # Verify color_rgb was cleared
        assert api_instance.color_rgb is None


@pytest.mark.asyncio
async def test_coordinator_cancel_transition_cancels_active_task(
    mock_hass, config_entry, mock_ble_device
):
    """Test that _cancel_transition cancels active transition task."""
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

        # Start transition but don't await it
        import asyncio

        task = asyncio.create_task(coordinator.set_brightness_with_transition(200, 1.0))

        # Give it time to start and create the internal task
        await asyncio.sleep(0.01)

        # Verify the internal transition task exists
        assert coordinator._transition_task is not None
        transition_task = coordinator._transition_task

        # Cancel the transition
        coordinator._cancel_transition()

        # Give the event loop time to process the cancellation
        await asyncio.sleep(0.01)

        # Internal transition task should be cancelled or done
        assert transition_task.cancelled() or transition_task.done()

        # Clean up the outer task
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_coordinator_cancel_transition_does_nothing_when_no_active_task(
    mock_hass, config_entry, mock_ble_device
):
    """Test that _cancel_transition does nothing when there's no active transition."""
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)

        # Cancel when there's no active transition - should not raise
        coordinator._cancel_transition()

        # No exception should be raised


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


@pytest.mark.asyncio
async def test_shutdown_disconnects_ble(mock_hass, config_entry, mock_ble_device):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.connection_state = "connected"
        api_instance.total_reconnections = 0
        api_instance.last_poll_time = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        await coordinator.async_shutdown()

        api_instance.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args",
    [
        ("set_power", (False,)),
        ("set_brightness", (50,)),
        ("set_color_rgb", (1, 2, 3)),
        ("set_color_temp", (4000,)),
    ],
)
async def test_instant_command_cancels_running_transition(
    mock_hass, config_entry, mock_ble_device, method, args
):
    """An instant command must stop a running transition from overwriting it."""
    import asyncio

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.brightness = 100
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        outer = asyncio.create_task(coordinator.set_brightness_with_transition(200, 1.0))
        await asyncio.sleep(0.01)
        transition_task = coordinator._transition_task

        await getattr(coordinator, method)(*args)
        await asyncio.sleep(0)

        assert transition_task.cancelled()
        await outer
