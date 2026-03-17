"""H6006 Protocol implementation for Govee H6006 BLE lights."""
from __future__ import annotations

import logging

from .base import GoveeProtocol
from ..const import MAX_KELVIN, MIN_KELVIN

_LOGGER = logging.getLogger(__name__)

_PACKET_LEN = 20
_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


class H6006Protocol(GoveeProtocol):
    """Protocol implementation for Govee H6006 lights.

    The H6006 uses a 20-byte BLE packet format with:
    - Command packets (head 0x33): Sent to device to control state
    - Response packets (head 0xAA): Received from device with state updates
    - XOR checksum in final byte for data integrity

    Protocol details:
    - Power: cmd=0x01, payload=[0x01 (on) | 0x00 (off)]
    - Brightness: cmd=0x04, payload=[0-255]
    - RGB color: cmd=0x05, payload=[0x02, R, G, B]
    - Color temp: cmd=0x05, payload=[0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold]
    """

    COMMAND_HEAD = 0x33
    REQUEST_HEAD = 0xAA

    def _build_frame(self, cmd: int, payload: list[int]) -> bytes:
        """Build a 20-byte command packet for the H6006 BLE protocol.

        Args:
            cmd: The command byte (e.g., 0x01 for power).
            payload: A list of bytes for the command payload.

        Returns:
            A 20-byte packet with XOR checksum in the final byte.
        """
        frame = [self.COMMAND_HEAD, cmd & 0xFF] + payload
        frame += [0] * (_PACKET_LEN - 1 - len(frame))
        checksum = 0
        for b in frame:
            checksum ^= b
        frame.append(checksum & 0xFF)
        return bytes(frame)

    def build_power_packet(self, on: bool) -> bytes:
        """Build a power command packet.

        Args:
            on: True to turn on, False to turn off.

        Returns:
            A 20-byte BLE packet to set device power state.
        """
        return self._build_frame(_POWER_CMD, [0x01 if on else 0x00])

    def build_brightness_packet(self, value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255). Values outside this range are clamped.

        Returns:
            A 20-byte BLE packet to set device brightness.
        """
        value = max(0, min(255, value))
        return self._build_frame(_BRIGHTNESS_CMD, [value])

    def build_color_rgb_packet(self, r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255). Values outside this range are clamped.
            g: Green intensity (0-255). Values outside this range are clamped.
            b: Blue intensity (0-255). Values outside this range are clamped.

        Returns:
            A 20-byte BLE packet to set device RGB color.
        """
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return self._build_frame(_COLOR_CMD, [0x02, r, g, b])

    def build_color_temp_packet(self, kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500). Values outside
                    this range are clamped.

        Returns:
            A 20-byte BLE packet to set device color temperature.
        """
        kelvin = max(MIN_KELVIN, min(MAX_KELVIN, kelvin))
        warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
        cold = 255 - warm
        return self._build_frame(_COLOR_CMD, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])

    def parse_notification(self, frame: bytearray) -> dict | None:
        """Parse a notification packet from the H6006 device.

        The H6006 sends notifications (head=0xAA) when state changes or in response
        to queries. Packets have a 20-byte structure with XOR checksum verification.

        Args:
            frame: Raw notification data received from the device.

        Returns:
            A dictionary containing parsed state values, or None if the packet
            is invalid. Possible keys:
            - "power": bool (True=on, False=off)
            - "brightness": int (0-255)
            - "color_rgb": tuple[int, int, int] (R, G, B)
            - "color_temp": int (Kelvin)
        """
        # Validate packet length
        if len(frame) < _PACKET_LEN:
            return None

        # Verify checksum
        xor = 0
        for b in frame[:19]:
            xor ^= b
        if (xor & 0xFF) != frame[19]:
            _LOGGER.warning("Received packet with bad checksum, discarding")
            return None

        # Verify packet head
        if frame[0] != self.REQUEST_HEAD:
            return None

        result: dict = {}
        try:
            cmd = frame[1]
            if cmd == _POWER_CMD:
                result["power"] = frame[2] == 0x01
                _LOGGER.debug(f"Notification: power={result['power']}")
            elif cmd == _BRIGHTNESS_CMD:
                result["brightness"] = frame[2]
                _LOGGER.debug(f"Notification: brightness={result['brightness']}")
            elif cmd == _COLOR_CMD:
                # Detect white mode by checking if R, G, B are all 0xFF
                is_white_mode = frame[3] == 0xFF and frame[4] == 0xFF and frame[5] == 0xFF
                if is_white_mode:
                    warm = frame[7]
                    result["color_temp"] = round(
                        MAX_KELVIN - (warm / 255) * (MAX_KELVIN - MIN_KELVIN)
                    )
                    _LOGGER.debug(f"Notification: color_temp={result['color_temp']}K (white mode)")
                else:
                    result["color_rgb"] = (frame[3], frame[4], frame[5])
                    _LOGGER.debug(f"Notification: color_rgb={result['color_rgb']}")
            return result if result else None
        except Exception as err:
            _LOGGER.error(f"Error parsing notification: {err}")
            return None
