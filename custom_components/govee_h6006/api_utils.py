from __future__ import annotations

from .protocols import H6006Protocol


class GoveePacket:
    """Packet builder for Govee H6006 BLE commands (Head 0x33).

    This is a backward-compatibility wrapper around H6006Protocol.
    New code should use protocols.py directly.
    """

    @staticmethod
    def power(on: bool) -> bytes:
        """Build a power command packet.

        Args:
            on: True for turn on, False for turn off.
        """
        return H6006Protocol.power(on)

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).
        """
        return H6006Protocol.brightness(value)

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).
        """
        return H6006Protocol.color_rgb(r, g, b)

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).
        """
        return H6006Protocol.color_temp(kelvin)
