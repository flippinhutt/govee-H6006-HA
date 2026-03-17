"""H6003 protocol implementation."""
from __future__ import annotations

from .base import GoveeProtocol, build_frame


class H6003Protocol(GoveeProtocol):
    """Protocol for Govee H6003 (RGB, 800 lm, 9W).

    RGB-only model without color temperature control.
    Basic commands expected to be identical to H6006 based on protocol research.
    Hardware verification pending.
    """

    MODEL_NAME = "H6003"
    DISCOVERY_PREFIX = "ihoment_H6003"
    HAS_COLOR_TEMP = False
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False

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
