import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.components.light import ColorMode
from custom_components.govee_h6006.light import GoveeLight
from custom_components.govee_h6006.coordinator import GoveeData


def make_coordinator(state=True, brightness=255, color_rgb=None, color_temp=None):
    coordinator = MagicMock()
    coordinator.data = GoveeData(
        state=state,
        brightness=brightness,
        color_rgb=color_rgb,
        color_temp=color_temp,
    )
    coordinator.set_power = AsyncMock()
    coordinator.set_brightness = AsyncMock()
    coordinator.set_color_rgb = AsyncMock()
    coordinator.set_color_temp = AsyncMock()
    coordinator.device_name = "ihoment_H6006"
    coordinator.device_address = "AA:BB:CC:DD:EE:FF"
    return coordinator


def make_light(coordinator):
    config_entry = MagicMock()
    config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    light = GoveeLight(coordinator, config_entry)
    return light


def test_light_is_on_when_state_true():
    light = make_light(make_coordinator(state=True))
    assert light.is_on is True

def test_light_is_off_when_state_false():
    light = make_light(make_coordinator(state=False))
    assert light.is_on is False

def test_brightness_exposed_correctly():
    light = make_light(make_coordinator(brightness=128))
    assert light.brightness == 128

def test_color_mode_rgb_when_color_set():
    light = make_light(make_coordinator(color_rgb=(255, 0, 0), color_temp=None))
    assert light.color_mode == ColorMode.RGB

def test_color_mode_color_temp_when_temp_set():
    light = make_light(make_coordinator(color_rgb=None, color_temp=3000))
    assert light.color_mode == ColorMode.COLOR_TEMP

def test_supported_color_modes():
    light = make_light(make_coordinator())
    assert ColorMode.RGB in light.supported_color_modes
    assert ColorMode.COLOR_TEMP in light.supported_color_modes

def test_color_temp_kelvin_range():
    light = make_light(make_coordinator())
    assert light.min_color_temp_kelvin == 2700
    assert light.max_color_temp_kelvin == 6500

@pytest.mark.asyncio
async def test_turn_on_calls_set_power():
    coordinator = make_coordinator(state=False)
    light = make_light(coordinator)
    await light.async_turn_on()
    coordinator.set_power.assert_called_once_with(True)

@pytest.mark.asyncio
async def test_turn_on_with_brightness():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(brightness=100)
    coordinator.set_brightness.assert_called_once_with(100)

@pytest.mark.asyncio
async def test_turn_on_with_rgb():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(rgb_color=(255, 128, 0))
    coordinator.set_color_rgb.assert_called_once_with(255, 128, 0)

@pytest.mark.asyncio
async def test_turn_on_with_color_temp():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(color_temp_kelvin=4000)
    coordinator.set_color_temp.assert_called_once_with(4000)

@pytest.mark.asyncio
async def test_turn_off():
    coordinator = make_coordinator(state=True)
    light = make_light(coordinator)
    await light.async_turn_off()
    coordinator.set_power.assert_called_once_with(False)
