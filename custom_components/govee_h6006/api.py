from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import cast

from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection

from .const import (
    MAX_KELVIN,
    MAX_RECONNECT_ATTEMPTS,
    MIN_KELVIN,
    READ_CHARACTERISTIC_UUID,
    RECONNECT_BACKOFF_BASE,
    RECONNECT_BACKOFF_MAX,
    RECONNECT_COOLDOWN_SECONDS,
    WRITE_CHARACTERISTIC_UUID,
)
from .protocols import H6006Protocol
from .protocols.base import GoveeProtocol

_LOGGER = logging.getLogger(__name__)

_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


class GoveeAPI:
    """Interface for Govee H6006 BLE device communication.

    Handles persistent Bluetooth connections, command execution, and notification
    parsing for Govee H6006 lights using the bleak library.

    Attributes:
        state: Current power state (True=on, False=off).
        brightness: Current brightness level (0-255).
        color_rgb: Current RGB color tuple (R, G, B).
        color_temp: Current color temperature in Kelvin.
        rssi: Last reported signal strength in dBm.
        total_reconnections: Total count of successful automatic reconnections.
    """

    def __init__(
        self,
        ble_device: BLEDevice,
        update_callback: Callable[[], Awaitable[None]],
        timeout: float = 20.0,
        max_attempts: int = 5,
        suppression_window: int = 500,
        protocol: GoveeProtocol | None = None,
    ) -> None:
        """Initialize the Govee API client.

        Args:
            ble_device: The Bluetooth device to connect to.
            update_callback: Async callback executed when device state changes.
            timeout: BLE operation timeout in seconds.
            max_attempts: Maximum number of connection attempts.
            suppression_window: Time in ms to suppress notifications after a command.
            protocol: Protocol implementation for packet building and parsing.
                     Defaults to H6006Protocol if not provided.
        """
        self._ble_device = ble_device
        self._update_callback = update_callback
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._suppression_window = suppression_window
        self._protocol = protocol if protocol is not None else H6006Protocol()
        self._last_callback_time = 0.0
        self._client: BleakClient | None = None
        self._connect_lock = asyncio.Lock()
        self._suppress_update_until = 0.0  # Suppress notifications after command for 500ms
        self.state: bool | None = None
        self.brightness: int | None = None
        self.color_rgb: tuple[int, int, int] | None = None
        self.color_temp: int | None = None
        # Connection state tracking
        self._reconnect_attempts: int = 0
        self._last_disconnect_time: float | None = None
        self._is_reconnecting: bool = False
        self._connection_lock: asyncio.Lock = asyncio.Lock()
        # Diagnostic metrics
        self.rssi: int | None = None
        # Track last 10 attempts (True=success, False=failure)
        self._connection_attempts: deque[bool] = deque(maxlen=10)
        self.last_poll_time: float | None = None  # Timestamp of last successful poll
        self.total_reconnections: int = 0  # Total number of successful reconnections

    @property
    def address(self) -> str:
        """Return the Bluetooth MAC address of the device."""
        return cast(str, self._ble_device.address)

    @property
    def is_available(self) -> bool:
        """Return True if device is available (connected or can reconnect)."""
        # If currently connected, device is available
        if self._client is not None and self._client.is_connected:
            return True

        # If max reconnection attempts exceeded, check cooldown period
        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            # If cooldown period has elapsed, reset counter and allow retry
            if self._last_disconnect_time is not None:
                cooldown_elapsed = time.time() - self._last_disconnect_time
                if cooldown_elapsed >= RECONNECT_COOLDOWN_SECONDS:
                    _LOGGER.info(
                        "Cooldown period (%ds) elapsed for %s, resetting attempts and retrying",
                        RECONNECT_COOLDOWN_SECONDS,
                        self.address
                    )
                    self._reconnect_attempts = 0
                    self._last_disconnect_time = None
                    return True
            # Cooldown not elapsed, device still unavailable
            return False

        # Under max attempts, device is available
        return True

    @property
    def connection_success_rate(self) -> float | None:
        """Return connection success rate (0-100) over last 10 attempts."""
        if not self._connection_attempts:
            return None
        successful = sum(1 for attempt in self._connection_attempts if attempt)
        return round((successful / len(self._connection_attempts)) * 100, 1)

    @property
    def connection_state(self) -> str:
        """Return human-readable connection state for diagnostics."""
        if self._client is not None and self._client.is_connected:
            return "connected"
        if self._is_reconnecting:
            return f"reconnecting (attempt {self._reconnect_attempts + 1}/{MAX_RECONNECT_ATTEMPTS})"
        if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            if self._last_disconnect_time is not None:
                elapsed = time.time() - self._last_disconnect_time
                cooldown_remaining = RECONNECT_COOLDOWN_SECONDS - elapsed
                if cooldown_remaining > 0:
                    return f"unavailable (cooldown {int(cooldown_remaining)}s remaining)"
            return "unavailable (max attempts exceeded)"
        return "disconnected"

    def update_device(self, ble_device: BLEDevice) -> None:
        """Refresh the BLE device handle.

        Call this before connecting if the device handle may be stale (e.g., from
        a discovery callback).

        Args:
            ble_device: The new BLEDevice handle.
        """
        self._ble_device = ble_device

    async def _retry_connection(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Returns True if reconnection succeeded, False if max attempts exceeded or skipped.
        Logs all attempts at debug level.
        """
        # Check if reconnection is already in progress
        if self._is_reconnecting:
            _LOGGER.debug(
                "Reconnection already in progress for %s, skipping",
                self.address
            )
            return False

        # Mark reconnection in progress before acquiring lock
        self._is_reconnecting = True

        try:
            async with self._connection_lock:
                # Check if already connected after acquiring lock
                if self._client is not None and self._client.is_connected:
                    _LOGGER.debug("Already connected to %s, no reconnection needed", self.address)
                    # Reset attempts counter since we're connected
                    self._reconnect_attempts = 0
                    return False  # No reconnection performed

                while self._reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                    # Calculate exponential backoff based on number of previous failures
                    # After N failures, wait base * (2 ** (N-1)) seconds: 1s, 2s, 4s, 8s...
                    if self._reconnect_attempts > 0:
                        backoff = min(
                            RECONNECT_BACKOFF_BASE * (2 ** (self._reconnect_attempts - 1)),
                            RECONNECT_BACKOFF_MAX
                        )
                        _LOGGER.debug(
                            "Reconnection attempt %d/%d for %s, waiting %.1fs",
                            self._reconnect_attempts + 1,
                            MAX_RECONNECT_ATTEMPTS,
                            self.address,
                            backoff
                        )
                        await asyncio.sleep(backoff)
                    else:
                        _LOGGER.debug(
                            "Reconnection attempt %d/%d for %s",
                            self._reconnect_attempts + 1,
                            MAX_RECONNECT_ATTEMPTS,
                            self.address
                        )

                    try:
                        # Attempt to establish connection
                        self._client = await establish_connection(
                            BleakClient,
                            self._ble_device,
                            self.address,
                            max_attempts=self._max_attempts,
                            ble_device_callback_timeout=self._timeout,
                        )
                        await self._client.start_notify(
                            READ_CHARACTERISTIC_UUID, self._handle_notification
                        )

                        # Success! Reset state and capture RSSI
                        self.rssi = self._ble_device.rssi
                        self._connection_attempts.append(True)  # Record successful connection
                        _LOGGER.debug(
                            "Reconnection successful for %s after %d attempts (RSSI: %s dBm)",
                            self.address,
                            self._reconnect_attempts + 1,
                            self.rssi
                        )
                        self._reconnect_attempts = 0
                        self._last_disconnect_time = None
                        self.total_reconnections += 1
                        return True

                    except Exception as err:
                        self._reconnect_attempts += 1
                        self._last_disconnect_time = time.time()
                        self._connection_attempts.append(False)  # Record failed connection
                        _LOGGER.debug(
                            "Reconnection attempt %d/%d failed for %s: %s",
                            self._reconnect_attempts,
                            MAX_RECONNECT_ATTEMPTS,
                            self.address,
                            err
                        )

                # Max attempts exceeded
                _LOGGER.warning(
                    "Max reconnection attempts (%d) exceeded for %s, marking unavailable",
                    MAX_RECONNECT_ATTEMPTS,
                    self.address
                )
                return False

        finally:
            self._is_reconnecting = False

    async def _ensure_connected(self) -> None:
        """Ensure the device is connected and notifications are started.

        Raises:
            ConnectionError: If connection cannot be established after retries.
        """
        if self._client is not None and self._client.is_connected:
            return
        # Use retry logic with exponential backoff
        success = await self._retry_connection()
        if not success:
            raise ConnectionError(
                f"Failed to connect to {self.address} after {MAX_RECONNECT_ATTEMPTS} attempts"
            )
        async with self._connect_lock:
            if self._client is not None and self._client.is_connected:
                return
            self._client = await establish_connection(
                BleakClient,
                self._ble_device,
                self.address,
                max_attempts=self._max_attempts,
                ble_device_callback_timeout=self._timeout,
            )
            await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._handle_notification)
            # Capture RSSI on successful connection
            self.rssi = self._ble_device.rssi

    def _build_query(self, cmd: int) -> bytes:
        """Build a 20-byte state-query packet using the protocol's REQUEST_HEAD.

        Args:
            cmd: The command byte to query (e.g., 0x01 for power).

        Returns:
            A 20-byte query packet with XOR checksum.
        """
        frame = [self._protocol.REQUEST_HEAD, cmd & 0xFF] + [0] * 17
        checksum = 0
        for b in frame:
            checksum ^= b
        frame.append(checksum & 0xFF)
        return bytes(frame)

    async def _write(self, packet: bytes) -> None:
        """Write a packet to the device's write characteristic.

        Args:
            packet: The 20-byte packet to write.
        """
        await self._ensure_connected()
        assert self._client is not None  # _ensure_connected raises if connection fails
        # Suppress state notifications for 500ms to prevent stale device state
        # from overwriting optimistic updates
        self._suppress_update_until = time.time() + 0.5
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, packet, False)

    async def _handle_notification(
        self, characteristic: BleakGATTCharacteristic | None, frame: bytearray
    ) -> None:
        # Suppress notifications for 500ms after sending a command
        # This prevents the device's old state from overwriting optimistic updates
        if time.time() < self._suppress_update_until:
            _LOGGER.debug("Suppressing notification (recent command in flight)")
            return

        # Parse notification using protocol
        # None = invalid packet (bad checksum, wrong format, etc.) - discard it
        # {} = valid packet but unknown/unhandled command - still notify
        # {fields} = valid packet with state updates
        parsed = self._protocol.parse_notification(frame)
        if parsed is None:
            return

        # Update internal state from parsed values (may be empty for unknown commands)
        if "power" in parsed:
            self.state = parsed["power"]
        if "brightness" in parsed:
            self.brightness = parsed["brightness"]
        if "color_rgb" in parsed:
            self.color_rgb = parsed["color_rgb"]
            self.color_temp = None  # clear stale color temp
        if "color_temp" in parsed:
            self.color_temp = parsed["color_temp"]
            self.color_rgb = None  # clear stale RGB

        # Throttle callbacks based on suppression window
        current_time = time.time() * 1000  # convert to milliseconds
        if current_time - self._last_callback_time >= self._suppression_window:
            await self._update_callback()
            self._last_callback_time = current_time
        # else: notification suppressed (too soon after last callback)

    async def poll_state(self) -> None:
        """Request current power, brightness, and color state from the device.

        Sends state-query commands for power, brightness, and color. Responses
        will flow back via the notification handler.
        """
        await self._ensure_connected()
        assert self._client is not None  # _ensure_connected raises if connection fails
        _LOGGER.debug("Polling device state")
        for cmd in (_POWER_CMD, _BRIGHTNESS_CMD, _COLOR_CMD):
            await self._client.write_gatt_char(
                WRITE_CHARACTERISTIC_UUID, self._build_query(cmd), False
            )
        # Record timestamp of successful poll
        self.last_poll_time = time.time()

    async def set_power(self, on: bool) -> None:
        """Set the power state of the device.

        Args:
            on: True to turn on, False to turn off.
        """
        _LOGGER.debug(f"Sending power command: on={on}")
        await self._write(self._protocol.build_power_packet(on))

    async def set_brightness(self, value: int) -> None:
        """Set the brightness level of the device.

        Args:
            value: Brightness level (0-255).
        """
        _LOGGER.debug(f"Sending brightness command: value={value}")
        await self._write(self._protocol.build_brightness_packet(value))

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        """Set the RGB color of the device.

        Args:
            r: Red value (0-255).
            g: Green value (0-255).
            b: Blue value (0-255).
        """
        _LOGGER.debug(f"Sending RGB command: r={r}, g={g}, b={b}")
        await self._write(self._protocol.build_color_rgb_packet(r, g, b))

    async def set_color_temp(self, kelvin: int) -> None:
        """Set the color temperature of the device.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).
        """
        _LOGGER.debug(f"Sending color temp command: kelvin={kelvin}")
        await self._write(self._protocol.build_color_temp_packet(kelvin))
