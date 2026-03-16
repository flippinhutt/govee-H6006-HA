from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_KELVIN, MIN_KELVIN
from .coordinator import GoveeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Govee H6006 light platform."""
    coordinator: GoveeCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([GoveeH6006Light(coordinator, config_entry)])


class GoveeH6006Light(CoordinatorEntity[GoveeCoordinator], LightEntity):  # type: ignore[misc]
    """Representation of a Govee H6006 BLE light.

    Maps Home Assistant light entity commands to GoveeCoordinator actions.
    """
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = MIN_KELVIN
    _attr_max_color_temp_kelvin = MAX_KELVIN

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize Govee light entity.

        Args:
            coordinator: The data update coordinator.
            config_entry: The config entry associated with this light.
        """
        super().__init__(coordinator)
        self._attr_unique_id = config_entry.unique_id
        self._attr_name = coordinator.device_name

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self.coordinator.data.state  # type: ignore[no-any-return]

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light."""
        return self.coordinator.data.brightness  # type: ignore[no-any-return]

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        return self.coordinator.data.color_rgb  # type: ignore[no-any-return]

    @property
    def color_temp(self) -> int | None:
        """Return the color_temp of the light."""
        return self.coordinator.data.color_temp  # type: ignore[no-any-return]

    @property
    def color_mode(self) -> ColorMode:
        if self.coordinator.data.color_temp is not None:
            return ColorMode.COLOR_TEMP
        return ColorMode.RGB

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return self._attr_supported_color_modes

    @property
    def min_color_temp_kelvin(self) -> int:
        return self._attr_min_color_temp_kelvin

    @property
    def max_color_temp_kelvin(self) -> int:
        return self._attr_max_color_temp_kelvin

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on.

        Args:
            **kwargs: Light attributes to set (brightness, rgb_color, color_temp_kelvin).
        """
        if not self.is_on:
            await self.coordinator.set_power(True)
        if "brightness" in kwargs:
            await self.coordinator.set_brightness(kwargs["brightness"])
        if "rgb_color" in kwargs:
            r, g, b = kwargs["rgb_color"]
            await self.coordinator.set_color_rgb(r, g, b)
        if "color_temp_kelvin" in kwargs:
            await self.coordinator.set_color_temp(kwargs["color_temp_kelvin"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.coordinator.set_power(False)
