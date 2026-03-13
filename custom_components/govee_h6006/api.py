from __future__ import annotations
import logging
from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection

from .const import WRITE_CHARACTERISTIC_UUID, READ_CHARACTERISTIC_UUID, MIN_KELVIN, MAX_KELVIN
from .api_utils import GoveePacket

_LOGGER = logging.getLogger(__name__)

_REQUEST_HEAD = 0xAA
_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


class GoveeAPI:
    def __init__(self, ble_device: BLEDevice, update_callback) -> None:
        self._ble_device = ble_device
        self._update_callback = update_callback
        self._client: BleakClient | None = None
        self.state: bool | None = None
        self.brightness: int | None = None
        self.color_rgb: tuple[int, int, int] | None = None
        self.color_temp: int | None = None

    @property
    def address(self) -> str:
        return self._ble_device.address

    async def _ensure_connected(self) -> None:
        if self._client is not None and self._client.is_connected:
            return
        self._client = await establish_connection(
            BleakClient, self._ble_device, self.address
        )
        await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._handle_notification)

    async def _write(self, packet: bytes) -> None:
        await self._ensure_connected()
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
        cmd = frame[1]
        if cmd == _POWER_CMD:
            self.state = frame[2] == 0x01
        elif cmd == _BRIGHTNESS_CMD:
            self.brightness = frame[2]
        elif cmd == _COLOR_CMD:
            if frame[6] == 0x01:  # white mode
                warm = frame[7]
                self.color_temp = round(MAX_KELVIN - (warm / 255) * (MAX_KELVIN - MIN_KELVIN))
                self.color_rgb = None  # clear stale RGB
            else:
                self.color_rgb = (frame[3], frame[4], frame[5])
                self.color_temp = None  # clear stale color temp
        await self._update_callback()

    async def set_power(self, on: bool) -> None:
        await self._write(GoveePacket.power(on))

    async def set_brightness(self, value: int) -> None:
        await self._write(GoveePacket.brightness(value))

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        await self._write(GoveePacket.color_rgb(r, g, b))

    async def set_color_temp(self, kelvin: int) -> None:
        await self._write(GoveePacket.color_temp(kelvin))
