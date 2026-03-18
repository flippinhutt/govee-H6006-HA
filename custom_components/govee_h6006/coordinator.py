from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import GoveeAPI
from .const import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_SUPPRESSION_WINDOW,
    DOMAIN,
    MAX_TRANSITION_DURATION,
    MIN_TRANSITION_DURATION,
    TRANSITION_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeData:
    """Snapshot of Govee device state for Home Assistant.

    Contains all state attributes to be consumed by Home Assistant entities.
    """

    state: bool | None = None
    brightness: int | None = None
    color_rgb: tuple[int, int, int] | None = None
    color_temp: int | None = None
    rssi: int | None = None
    connection_success_rate: float | None = None
    last_poll_time: datetime | None = None
    connection_state: str = "disconnected"
    total_reconnections: int = 0
    firmware_version: str | None = None
    hardware_version: str | None = None
    model_number: str | None = None


class GoveeCoordinator(DataUpdateCoordinator[GoveeData]):  # type: ignore[misc]
    """Manage fetching data and sending commands to a Govee BLE device.

    Coordinates state updates via both push notifications (primary) and
    periodic polling (fallback). Handles optimistic state updates for UI responsiveness.
    """

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize Govee coordinator.

        Args:
            hass: Home Assistant instance.
            config_entry: Integration config entry.
        """
        self.device_address = config_entry.data["address"]
        self.device_name = config_entry.data["name"]
        model_type = config_entry.data.get("model", "H6006")

        ble_device = bluetooth.async_ble_device_from_address(
            hass, self.device_address, connectable=True
        )
        if ble_device is None:
            _LOGGER.debug(
                "BLE device %s not found in cache during coordinator init",
                self.device_address,
            )
            # Create a placeholder BLEDevice if not found in cache.
            # GoveeAPI will refresh this in _async_update_data.
            ble_device = BLEDevice(self.device_address, self.device_name, {})

        connection_timeout = config_entry.options.get(
            "connection_timeout", DEFAULT_CONNECTION_TIMEOUT
        )
        max_retries = config_entry.options.get("max_retries", DEFAULT_MAX_RETRIES)
        suppression_window = config_entry.options.get(
            "suppression_window", DEFAULT_SUPPRESSION_WINDOW
        )

        self._api = GoveeAPI(
            ble_device,
            self._async_push_data,
            timeout=connection_timeout,
            max_attempts=max_retries,
            suppression_window=suppression_window,
            model_type=model_type,
        )

        # Query device info on initialization
        # Schedule as a task to not block coordinator setup
        async def _init_device_info() -> None:
            """Query device information and log firmware version."""
            try:
                # Use fast-fail limit during setup
                await self._api.query_device_info(max_attempts=2)
                if self._api.firmware_version:
                    _LOGGER.info(
                        f"Connected to {self.device_name} - "
                        f"Firmware: {self._api.firmware_version}, "
                        f"Hardware: {self._api.hardware_version}, "
                        f"Model: {self._api.model_number}"
                    )
                else:
                    _LOGGER.debug("Device info not available from device")
            except Exception as err:
                _LOGGER.debug(f"Failed to query device info: {err}")

        # Schedule the task and store handle for cancellation on shutdown
        self._device_info_task = hass.async_create_task(_init_device_info())

        polling_interval = config_entry.options.get("polling_interval", DEFAULT_POLLING_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.device_address})",
            update_interval=timedelta(seconds=polling_interval),
        )

        # Initialize data with current API state
        self.data = self._snapshot()

        # Track active transition task for cancellation
        self._transition_task: asyncio.Task[None] | None = None

        # Track if this is the first refresh to apply fast-fail logic
        self._first_refresh = True

    async def async_shutdown(self) -> None:
        """Cancel background tasks on shutdown."""
        if self._device_info_task and not self._device_info_task.done():
            self._device_info_task.cancel()
        await super().async_shutdown()

    @property
    def available(self) -> bool:
        """Return True if the device is available (connected or can reconnect)."""
        return self._api.is_available

    def _snapshot(self) -> GoveeData:
        """Create a snapshot of the current API state.

        Returns:
            A GoveeData object containing all relevant state attributes.
        """
        return GoveeData(
            state=self._api.state,
            brightness=self._api.brightness,
            color_rgb=self._api.color_rgb,
            color_temp=self._api.color_temp,
            rssi=self._api.rssi,
            connection_success_rate=self._api.connection_success_rate,
            last_poll_time=(
                dt_util.utc_from_timestamp(self._api.last_poll_time)
                if self._api.last_poll_time
                else None
            ),
            connection_state=self._api.connection_state,
            total_reconnections=self._api.total_reconnections,
            firmware_version=self._api.firmware_version,
            hardware_version=self._api.hardware_version,
            model_number=self._api.model_number,
        )

    async def _async_push_data(self) -> None:
        """Update coordinator data from push notification."""
        self.async_set_updated_data(self._snapshot())

    def _cancel_transition(self) -> None:
        """Cancel any active transition task."""
        if self._transition_task and not self._transition_task.done():
            self._transition_task.cancel()
            _LOGGER.debug("Cancelled active transition task")

    async def _async_update_data(self) -> GoveeData:
        """Fetch latest state from device via polling.

        Executed periodically by the DataUpdateCoordinator.

        Returns:
            The latest GoveeData snapshot.

        Raises:
            UpdateFailed: If device is unavailable or communication fails.
        """
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
                f"Device {self.device_address} is unavailable "
                f"(state: {self._api.connection_state})"
            )

        try:
            # For the first refresh, fail fast (2 attempts) to avoid hanging HA setup
            # 2 attempts: 0s wait + 20s timeout + 1s wait + 20s timeout = ~41s max
            max_attempts = 2 if self._first_refresh else None
            await self._api.poll_state(max_attempts=max_attempts)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with {self.device_address}: {err}") from err
        finally:
            self._first_refresh = False

        return self._snapshot()

    async def set_power(self, on: bool) -> None:
        """Set power state with optimistic UI update.

        Args:
            on: True to turn on, False to turn off.

        Raises:
            HomeAssistantError: If command execution fails.
        """
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
        """Set brightness with optimistic UI update.

        Args:
            value: Brightness level (0-255).

        Raises:
            HomeAssistantError: If command execution fails.
        """
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
        """Set RGB color with optimistic UI update.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).

        Raises:
            HomeAssistantError: If command execution fails.
        """
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
        """Set color temperature with optimistic UI update.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).

        Raises:
            HomeAssistantError: If command execution fails.
        """
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

    async def set_brightness_with_transition(self, value: int, transition: float) -> None:
        """Set brightness with smooth transition.

        Args:
            value: Target brightness level (0-255).
            transition: Transition duration in seconds.

        Raises:
            HomeAssistantError: If command execution fails.
        """
        # Cancel any active transition
        self._cancel_transition()

        # Clamp transition duration to allowed range
        transition = max(MIN_TRANSITION_DURATION, min(MAX_TRANSITION_DURATION, transition))

        # If transition is very short or device is off, fall back to instant change
        if transition < MIN_TRANSITION_DURATION or self._api.brightness is None:
            await self.set_brightness(value)
            return

        # Create and track transition task
        self._transition_task = asyncio.create_task(
            self._run_brightness_transition(value, transition)
        )

        try:
            await self._transition_task
        except asyncio.CancelledError:
            _LOGGER.debug("Brightness transition cancelled")
            # Don't raise - cancellation is expected when a new command arrives

    async def _run_brightness_transition(self, target: int, duration: float) -> None:
        """Run brightness transition interpolation.

        Args:
            target: Target brightness level (0-255).
            duration: Transition duration in seconds.
        """
        start = self._api.brightness
        if start is None:
            return

        # Calculate number of steps
        steps = int(duration / TRANSITION_UPDATE_INTERVAL)
        if steps < 1:
            steps = 1

        # Interpolate and send intermediate values
        for step in range(1, steps + 1):
            # Linear interpolation
            progress = step / steps
            interpolated = int(start + (target - start) * progress)

            # Send brightness command (without optimistic update to avoid flicker)
            prev_brightness = self._api.brightness
            try:
                await self._api.set_brightness(interpolated)
                # Update internal state
                self._api.brightness = interpolated
                self.async_set_updated_data(self._snapshot())
            except Exception as err:
                _LOGGER.warning(f"Failed to send transition step: {err}")
                # Rollback and abort transition
                self._api.brightness = prev_brightness
                self.async_set_updated_data(self._snapshot())
                return

            # Wait before next update (unless this is the last step)
            if step < steps:
                await asyncio.sleep(TRANSITION_UPDATE_INTERVAL)

    async def set_color_rgb_with_transition(
        self, r: int, g: int, b: int, transition: float
    ) -> None:
        """Set RGB color with smooth transition.

        Args:
            r: Target red intensity (0-255).
            g: Target green intensity (0-255).
            b: Target blue intensity (0-255).
            transition: Transition duration in seconds.

        Raises:
            HomeAssistantError: If command execution fails.
        """
        # Cancel any active transition
        self._cancel_transition()

        # Clamp transition duration to allowed range
        transition = max(MIN_TRANSITION_DURATION, min(MAX_TRANSITION_DURATION, transition))

        # If transition is very short or no current color, fall back to instant change
        if transition < MIN_TRANSITION_DURATION or self._api.color_rgb is None:
            await self.set_color_rgb(r, g, b)
            return

        # Create and track transition task
        self._transition_task = asyncio.create_task(
            self._run_color_rgb_transition((r, g, b), transition)
        )

        try:
            await self._transition_task
        except asyncio.CancelledError:
            _LOGGER.debug("RGB color transition cancelled")
            # Don't raise - cancellation is expected when a new command arrives

    async def _run_color_rgb_transition(
        self, target: tuple[int, int, int], duration: float
    ) -> None:
        """Run RGB color transition interpolation.

        Args:
            target: Target RGB color (r, g, b).
            duration: Transition duration in seconds.
        """
        start = self._api.color_rgb
        if start is None:
            return

        # Calculate number of steps
        steps = int(duration / TRANSITION_UPDATE_INTERVAL)
        if steps < 1:
            steps = 1

        # Interpolate and send intermediate values
        for step in range(1, steps + 1):
            # Linear interpolation per color channel
            progress = step / steps
            interpolated_r = int(start[0] + (target[0] - start[0]) * progress)
            interpolated_g = int(start[1] + (target[1] - start[1]) * progress)
            interpolated_b = int(start[2] + (target[2] - start[2]) * progress)

            # Send color command (without optimistic update to avoid flicker)
            prev_color_rgb = self._api.color_rgb
            prev_color_temp = self._api.color_temp
            try:
                await self._api.set_color_rgb(interpolated_r, interpolated_g, interpolated_b)
                # Update internal state
                self._api.color_rgb = (interpolated_r, interpolated_g, interpolated_b)
                self._api.color_temp = None  # clear color temp when RGB is set
                self.async_set_updated_data(self._snapshot())
            except Exception as err:
                _LOGGER.warning(f"Failed to send transition step: {err}")
                # Rollback and abort transition
                self._api.color_rgb = prev_color_rgb
                self._api.color_temp = prev_color_temp
                self.async_set_updated_data(self._snapshot())
                return

            # Wait before next update (unless this is the last step)
            if step < steps:
                await asyncio.sleep(TRANSITION_UPDATE_INTERVAL)

    async def set_color_temp_with_transition(self, kelvin: int, transition: float) -> None:
        """Set color temperature with smooth transition.

        Args:
            kelvin: Target color temperature in Kelvin (2700-6500).
            transition: Transition duration in seconds.

        Raises:
            HomeAssistantError: If command execution fails.
        """
        # Cancel any active transition
        self._cancel_transition()

        # Clamp transition duration to allowed range
        transition = max(MIN_TRANSITION_DURATION, min(MAX_TRANSITION_DURATION, transition))

        # If transition is very short or no current color temp, fall back to instant change
        if transition < MIN_TRANSITION_DURATION or self._api.color_temp is None:
            await self.set_color_temp(kelvin)
            return

        # Create and track transition task
        self._transition_task = asyncio.create_task(
            self._run_color_temp_transition(kelvin, transition)
        )

        try:
            await self._transition_task
        except asyncio.CancelledError:
            _LOGGER.debug("Color temperature transition cancelled")
            # Don't raise - cancellation is expected when a new command arrives

    async def _run_color_temp_transition(self, target: int, duration: float) -> None:
        """Run color temperature transition interpolation.

        Args:
            target: Target color temperature in Kelvin (2700-6500).
            duration: Transition duration in seconds.
        """
        start = self._api.color_temp
        if start is None:
            return

        # Calculate number of steps
        steps = int(duration / TRANSITION_UPDATE_INTERVAL)
        if steps < 1:
            steps = 1

        # Interpolate and send intermediate values
        for step in range(1, steps + 1):
            # Linear interpolation
            progress = step / steps
            interpolated = int(start + (target - start) * progress)

            # Send color temp command (without optimistic update to avoid flicker)
            prev_color_rgb = self._api.color_rgb
            prev_color_temp = self._api.color_temp
            try:
                await self._api.set_color_temp(interpolated)
                # Update internal state
                self._api.color_temp = interpolated
                self._api.color_rgb = None  # clear RGB when color temp is set
                self.async_set_updated_data(self._snapshot())
            except Exception as err:
                _LOGGER.warning(f"Failed to send transition step: {err}")
                # Rollback and abort transition
                self._api.color_rgb = prev_color_rgb
                self._api.color_temp = prev_color_temp
                self.async_set_updated_data(self._snapshot())
                return

            # Wait before next update (unless this is the last step)
            if step < steps:
                await asyncio.sleep(TRANSITION_UPDATE_INTERVAL)
