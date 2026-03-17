"""H6009 protocol implementation."""
from __future__ import annotations

from .base import GoveeProtocol, build_frame


class H6009Protocol(GoveeProtocol):
    """Protocol for Govee H6009 (RGBWW, 1200 lm, 12W).

    Enhanced brightness model with music sync and scene modes.
    Basic commands expected to be identical to H6006 based on protocol research.
    Hardware verification pending for advanced features (music sync, scenes).
    """

    MODEL_NAME = "H6009"
    DISCOVERY_PREFIX = "ihoment_H6009"
    HAS_COLOR_TEMP = True
    HAS_MUSIC_SYNC = True
    HAS_SCENE_MODES = True
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
        kelvin = max(H6009Protocol.MIN_KELVIN, min(H6009Protocol.MAX_KELVIN, kelvin))
        warm = round(
            (H6009Protocol.MAX_KELVIN - kelvin)
            / (H6009Protocol.MAX_KELVIN - H6009Protocol.MIN_KELVIN)
            * 255
        )
        cold = 255 - warm
        return build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
