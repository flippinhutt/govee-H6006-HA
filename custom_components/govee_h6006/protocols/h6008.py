"""H6008 protocol implementation."""
from __future__ import annotations

import math

from .base import GoveeProtocol, build_frame

_COLOR_MODE = 0x0D


def _kelvin_tint(kelvin: int) -> tuple[int, int, int]:
    """Approximate RGB of a black body at 1900-6600 K (Tanner Helland's fit).

    The Govee app sends this tint along with the Kelvin value.
    """
    t = kelvin / 100
    green = 99.4708025861 * math.log(t) - 161.1195681661
    blue = 138.5177312231 * math.log(t - 10) - 305.0447927307
    return 255, max(0, min(255, round(green))), max(0, min(255, round(blue)))


class H6008Protocol(GoveeProtocol):
    """Protocol for Govee H6008 (RGBWW, 800 lm, 9W).

    Hardware-verified on hardware version 1.02.01 (unencrypted BLE advertisement).
    Differs from the H6006: brightness is a percentage, and color uses mode 0x0D.
    The bulb rejects the H6006's mode 0x02 frames with status 0x01.
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
            value: Brightness level (0-255), sent as a percentage (1-100).

        Returns:
            20-byte BLE command packet.
        """
        percent = max(1, min(100, round(value * 100 / 255)))
        return build_frame(0x04, [percent])

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
        return build_frame(0x05, [_COLOR_MODE, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Format: 0x0D, tint RGB, Kelvin (big-endian), tint RGB. Kelvin is rounded to
        100 K steps like the Govee app does.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).

        Returns:
            20-byte BLE command packet.
        """
        kelvin = round(kelvin / 100) * 100
        kelvin = max(H6008Protocol.MIN_KELVIN, min(H6008Protocol.MAX_KELVIN, kelvin))
        tint = _kelvin_tint(kelvin)
        return build_frame(0x05, [_COLOR_MODE, *tint, kelvin >> 8, kelvin & 0xFF, *tint])

    @staticmethod
    def parse_brightness(raw: int) -> int:
        """Convert the bulb's percentage (aa 04) to Home Assistant's 0-255 scale.

        Args:
            raw: Byte 2 of the reply, a percentage.

        Returns:
            Brightness level (0-255).
        """
        return min(255, round(raw * 255 / 100))

    @classmethod
    def parse_color(
        cls, frame: bytes
    ) -> tuple[tuple[int, int, int] | None, int | None] | None:
        """Parse a color reply: aa 05 0d R G B K_hi K_lo.

        A non-zero Kelvin means color temperature mode; R G B is then only the tint.

        Args:
            frame: The 20-byte reply.

        Returns:
            (rgb, kelvin), or None for modes other than 0x0D (e.g. scenes).
        """
        if frame[2] != _COLOR_MODE:
            return None
        kelvin = frame[6] << 8 | frame[7]
        if kelvin:
            return None, kelvin
        return (frame[3], frame[4], frame[5]), None
