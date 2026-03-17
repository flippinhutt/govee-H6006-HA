"""H6008 protocol implementation."""
from __future__ import annotations

from .base import GoveeProtocol, build_frame


class H6008Protocol(GoveeProtocol):
    """Protocol for Govee H6008 (RGBWW, 800 lm, 9W).

    Expected to be functionally identical to H6006 based on protocol research.
    Hardware verification pending.
    """

    MODEL_NAME = "H6008"
    DISCOVERY_PREFIX = "ihoment_H6008"
    HAS_COLOR_TEMP = True
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False
    MIN_KELVIN = 2700
    MAX_KELVIN = 6500

    @staticmethod
    def power(on: bool) -> bytes:
        """Build a power command packet.

        Args:
            on: True for turn on, False for turn off.

        Returns:
            20-byte BLE command packet.
        """
        return build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).

        Returns:
            20-byte BLE command packet.
        """
        value = max(0, min(255, value))
        return build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).

        Returns:
            20-byte BLE command packet.
        """
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return build_frame(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).

        Returns:
            20-byte BLE command packet.
        """
        kelvin = max(H6008Protocol.MIN_KELVIN, min(H6008Protocol.MAX_KELVIN, kelvin))
        warm = round(
            (H6008Protocol.MAX_KELVIN - kelvin)
            / (H6008Protocol.MAX_KELVIN - H6008Protocol.MIN_KELVIN)
            * 255
        )
        cold = 255 - warm
        return build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
