from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoveeAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeData:
    state: bool | None = None
    brightness: int | None = None
    color_rgb: tuple[int, int, int] | None = None
    color_temp: int | None = None


class GoveeCoordinator(DataUpdateCoordinator[GoveeData]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.device_address = config_entry.data["address"]
        self.device_name = config_entry.data["name"]

        ble_device = bluetooth.async_ble_device_from_address(
            hass, self.device_address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(f"BLE device {self.device_address} not found")

        self._api = GoveeAPI(ble_device, self._async_push_data)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.device_address})",
            update_interval=timedelta(seconds=30),
        )

        # Initialize data with current API state
        self.data = self._snapshot()

    @property
    def available(self) -> bool:
        """Return True if the device is available (connected or can reconnect)."""
        return self._api.is_available

    def _snapshot(self) -> GoveeData:
        return GoveeData(
            state=self._api.state,
            brightness=self._api.brightness,
            color_rgb=self._api.color_rgb,
            color_temp=self._api.color_temp,
        )

    async def _async_push_data(self) -> None:
        self.async_set_updated_data(self._snapshot())

    async def _async_update_data(self) -> GoveeData:
        # Refresh the BLE device handle in case it has gone stale since init.
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.device_address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(f"BLE device {self.device_address} not found")
        self._api.update_device(ble_device)

        # Check if device is available before polling
        if not self._api.is_available:
            raise UpdateFailed(
                f"Device {self.device_address} is unavailable after max reconnection attempts"
            )

        try:
            await self._api.poll_state()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with {self.device_address}: {err}") from err

        return self._snapshot()

    async def set_power(self, on: bool) -> None:
        # Save previous state for rollback on failure
        prev_state = self._api.state

        # Optimistic update for instant UI response
        self._api.state = on
        self.async_set_updated_data(self._snapshot())

        try:
            await self._api.set_power(on)
        except Exception as err:
            # Rollback to previous state on failure
            self._api.state = prev_state
            self.async_set_updated_data(self._snapshot())
            raise HomeAssistantError(f"Failed to set power state: {err}") from err

    async def set_brightness(self, value: int) -> None:
        # Save previous state for rollback on failure
        prev_brightness = self._api.brightness

        # Optimistic update for instant UI response
        self._api.brightness = value
        self.async_set_updated_data(self._snapshot())

        try:
            await self._api.set_brightness(value)
        except Exception as err:
            # Rollback to previous state on failure
            self._api.brightness = prev_brightness
            self.async_set_updated_data(self._snapshot())
            raise HomeAssistantError(f"Failed to set brightness: {err}") from err

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        # Save previous state for rollback on failure
        prev_color_rgb = self._api.color_rgb
        prev_color_temp = self._api.color_temp

        # Optimistic update for instant UI response
        self._api.color_rgb = (r, g, b)
        self._api.color_temp = None  # clear color temp when RGB is set
        self.async_set_updated_data(self._snapshot())

        try:
            await self._api.set_color_rgb(r, g, b)
        except Exception as err:
            # Rollback to previous state on failure
            self._api.color_rgb = prev_color_rgb
            self._api.color_temp = prev_color_temp
            self.async_set_updated_data(self._snapshot())
            raise HomeAssistantError(f"Failed to set color RGB: {err}") from err

    async def set_color_temp(self, kelvin: int) -> None:
        # Save previous state for rollback on failure
        prev_color_rgb = self._api.color_rgb
        prev_color_temp = self._api.color_temp

        # Optimistic update for instant UI response
        self._api.color_temp = kelvin
        self._api.color_rgb = None  # clear RGB when color temp is set
        self.async_set_updated_data(self._snapshot())

        try:
            await self._api.set_color_temp(kelvin)
        except Exception as err:
            # Rollback to previous state on failure
            self._api.color_rgb = prev_color_rgb
            self._api.color_temp = prev_color_temp
            self.async_set_updated_data(self._snapshot())
            raise HomeAssistantError(f"Failed to set color temperature: {err}") from err
