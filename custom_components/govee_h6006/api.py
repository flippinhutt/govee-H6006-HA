from __future__ import annotations
import asyncio
from collections import deque
import logging
import time
from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection

from .const import (
    WRITE_CHARACTERISTIC_UUID,
    READ_CHARACTERISTIC_UUID,
    MIN_KELVIN,
    MAX_KELVIN,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_BACKOFF_BASE,
    RECONNECT_BACKOFF_MAX,
    RECONNECT_COOLDOWN_SECONDS,
)
from .api_utils import GoveePacket

_LOGGER = logging.getLogger(__name__)

_REQUEST_HEAD = 0xAA
_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


def _build_query(cmd: int) -> bytes:
    """Build a 20-byte state-query packet (head=0xAA) for the given command."""
    frame = [_REQUEST_HEAD, cmd & 0xFF] + [0] * 17
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)


class GoveeAPI:
    def __init__(
        self,
        ble_device: BLEDevice,
        update_callback,
        timeout: float = 15.0,
        max_attempts: int = 5,
        suppression_window: int = 500,
    ) -> None:
        self._ble_device = ble_device
        self._update_callback = update_callback
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._suppression_window = suppression_window
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
        self._connection_attempts: deque[bool] = deque(maxlen=10)  # Track last 10 attempts (True=success, False=failure)
        self.last_poll_time: float | None = None  # Timestamp of last successful poll
        self.total_reconnections: int = 0  # Total number of successful reconnections

    @property
    def address(self) -> str:
        return self._ble_device.address

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
                        "Cooldown period (%ds) elapsed for %s, resetting reconnection counter and retrying",
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
        """Return connection success rate as percentage (0-100) over last 10 attempts, or None if no attempts."""
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
                cooldown_remaining = RECONNECT_COOLDOWN_SECONDS - (time.time() - self._last_disconnect_time)
                if cooldown_remaining > 0:
                    return f"unavailable (cooldown {int(cooldown_remaining)}s remaining)"
            return "unavailable (max attempts exceeded)"
        return "disconnected"

    def update_device(self, ble_device: BLEDevice) -> None:
        """Refresh the BLE device handle (call before connecting if handle may be stale)."""
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
                            BleakClient, self._ble_device, self.address
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
                BleakClient, self._ble_device, self.address, timeout=20.0
            )
            await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._handle_notification)
            # Capture RSSI on successful connection
            self.rssi = self._ble_device.rssi

    async def _write(self, packet: bytes) -> None:
        await self._ensure_connected()
        # Suppress state notifications for 500ms to prevent stale device state
        # from overwriting optimistic updates
        self._suppress_update_until = time.time() + 0.5
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, packet, False)

    async def _handle_notification(
        self, characteristic: BleakGATTCharacteristic | None, frame: bytearray
    ) -> None:
        if len(frame) < 20:
            return
        xor = 0
        for b in frame[:19]:
            xor ^= b
        if (xor & 0xFF) != frame[19]:
            _LOGGER.warning("Received packet with bad checksum, discarding")
            return
        if frame[0] != _REQUEST_HEAD:
            return

        # Suppress notifications for 500ms after sending a command
        # This prevents the device's old state from overwriting optimistic updates
        if time.time() < self._suppress_update_until:
            _LOGGER.debug("Suppressing notification (recent command in flight)")
            return

        cmd = frame[1]
        try:
            if cmd == _POWER_CMD:
                self.state = frame[2] == 0x01
                _LOGGER.debug(f"Notification: power={self.state}")
            elif cmd == _BRIGHTNESS_CMD:
                self.brightness = frame[2]
                _LOGGER.debug(f"Notification: brightness={self.brightness}")
            elif cmd == _COLOR_CMD:
                # Detect white mode by checking if R, G, B are all 0xFF
                is_white_mode = frame[3] == 0xFF and frame[4] == 0xFF and frame[5] == 0xFF
                if is_white_mode:
                    warm = frame[7]
                    self.color_temp = round(MAX_KELVIN - (warm / 255) * (MAX_KELVIN - MIN_KELVIN))
                    self.color_rgb = None  # clear stale RGB
                    _LOGGER.debug(f"Notification: color_temp={self.color_temp}K (white mode)")
                else:
                    self.color_rgb = (frame[3], frame[4], frame[5])
                    self.color_temp = None  # clear stale color temp
                    _LOGGER.debug(f"Notification: color_rgb={self.color_rgb}")
            else:
                self.color_rgb = (frame[3], frame[4], frame[5])
                self.color_temp = None  # clear stale color temp

        # Throttle callbacks based on suppression window
        current_time = time.time() * 1000  # convert to milliseconds
        if current_time - self._last_callback_time >= self._suppression_window:
            await self._update_callback()
            self._last_callback_time = current_time
        # else: notification suppressed (too soon after last callback)

    async def poll_state(self) -> None:
        """Request current power, brightness, and color state from the device."""
        await self._ensure_connected()
        _LOGGER.debug("Polling device state")
        for cmd in (_POWER_CMD, _BRIGHTNESS_CMD, _COLOR_CMD):
            await self._client.write_gatt_char(
                WRITE_CHARACTERISTIC_UUID, _build_query(cmd), False
            )
        # Record timestamp of successful poll
        self.last_poll_time = time.time()

    async def set_power(self, on: bool) -> None:
        _LOGGER.debug(f"Sending power command: on={on}")
        await self._write(GoveePacket.power(on))

    async def set_brightness(self, value: int) -> None:
        _LOGGER.debug(f"Sending brightness command: value={value}")
        await self._write(GoveePacket.brightness(value))

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        _LOGGER.debug(f"Sending RGB command: r={r}, g={g}, b={b}")
        await self._write(GoveePacket.color_rgb(r, g, b))

    async def set_color_temp(self, kelvin: int) -> None:
        _LOGGER.debug(f"Sending color temp command: kelvin={kelvin}")
        await self._write(GoveePacket.color_temp(kelvin))
