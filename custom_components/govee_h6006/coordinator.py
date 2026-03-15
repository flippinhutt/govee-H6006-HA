from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoveeAPI
from .const import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_SUPPRESSION_WINDOW,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeData:
    state: bool | None = None
    brightness: int | None = None
    color_rgb: tuple[int, int, int] | None = None
    color_temp: int | None = None
    rssi: int | None = None
    connection_success_rate: float | None = None
    last_poll_time: datetime | None = None
    connection_state: str = "disconnected"
    total_reconnections: int = 0


class GoveeCoordinator(DataUpdateCoordinator[GoveeData]):  # type: ignore[misc]
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.device_address = config_entry.data["address"]
        self.device_name = config_entry.data["name"]

        ble_device = bluetooth.async_ble_device_from_address(
            hass, self.device_address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(f"BLE device {self.device_address} not found")

        connection_timeout = config_entry.options.get("connection_timeout", DEFAULT_CONNECTION_TIMEOUT)
        max_retries = config_entry.options.get("max_retries", DEFAULT_MAX_RETRIES)
        suppression_window = config_entry.options.get("suppression_window", DEFAULT_SUPPRESSION_WINDOW)

        self._api = GoveeAPI(
            ble_device,
            self._async_push_data,
            timeout=connection_timeout,
            max_attempts=max_retries,
            suppression_window=suppression_window,
        )

        polling_interval = config_entry.options.get("polling_interval", DEFAULT_POLLING_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.device_address})",
            update_interval=timedelta(seconds=polling_interval),
        )

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
            rssi=self._api.rssi,
            connection_success_rate=self._api.connection_success_rate,
            last_poll_time=datetime.fromtimestamp(self._api.last_poll_time) if self._api.last_poll_time else None,
            connection_state=self._api.connection_state,
            total_reconnections=self._api.total_reconnections,
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
        # Optimistic update for instant UI response
        self._api.state = on
        self.async_set_updated_data(self._snapshot())
        await self._api.set_power(on)

    async def set_brightness(self, value: int) -> None:
        # Optimistic update for instant UI response
        self._api.brightness = value
        self.async_set_updated_data(self._snapshot())
        await self._api.set_brightness(value)

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        # Optimistic update for instant UI response
        self._api.color_rgb = (r, g, b)
        self._api.color_temp = None  # clear color temp when RGB is set
        self.async_set_updated_data(self._snapshot())
        await self._api.set_color_rgb(r, g, b)

    async def set_color_temp(self, kelvin: int) -> None:
        # Optimistic update for instant UI response
        self._api.color_temp = kelvin
        self._api.color_rgb = None  # clear RGB when color temp is set
        self.async_set_updated_data(self._snapshot())
        await self._api.set_color_temp(kelvin)
