from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
            update_interval=timedelta(seconds=15),
        )

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
        return self._snapshot()

    async def set_power(self, on: bool) -> None:
        await self._api.set_power(on)

    async def set_brightness(self, value: int) -> None:
        await self._api.set_brightness(value)

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        await self._api.set_color_rgb(r, g, b)

    async def set_color_temp(self, kelvin: int) -> None:
        await self._api.set_color_temp(kelvin)
