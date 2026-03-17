"""Base protocol abstraction for Govee BLE devices."""
from __future__ import annotations

from abc import ABC, abstractmethod


class GoveeProtocol(ABC):
    """Abstract base class for Govee BLE device protocols.

    Each Govee device model may have its own protocol implementation with
    different packet structures, command heads, or notification parsing logic.
    Concrete implementations override the abstract methods to provide
    model-specific command building and state parsing.

    Attributes:
        COMMAND_HEAD: Packet header byte for commands (e.g., 0x33 for H6006).
        REQUEST_HEAD: Packet header byte for state queries/responses (e.g., 0xAA for H6006).
    """

    COMMAND_HEAD: int
    REQUEST_HEAD: int

    @abstractmethod
    def build_power_packet(self, on: bool) -> bytes:
        """Build a power command packet.

        Args:
            on: True to turn on, False to turn off.

        Returns:
            A complete BLE packet ready to send to the device.
        """
        pass

    @abstractmethod
    def build_brightness_packet(self, value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (typically 0-255).

        Returns:
            A complete BLE packet ready to send to the device.
        """
        pass

    @abstractmethod
    def build_color_rgb_packet(self, r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (typically 0-255).
            g: Green intensity (typically 0-255).
            b: Blue intensity (typically 0-255).

        Returns:
            A complete BLE packet ready to send to the device.
        """
        pass

    @abstractmethod
    def build_color_temp_packet(self, kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Args:
            kelvin: Color temperature in Kelvin (typically 2700-6500).

        Returns:
            A complete BLE packet ready to send to the device.
        """
        pass

    @abstractmethod
    def parse_notification(self, frame: bytearray) -> dict | None:
        """Parse a notification packet from the device.

        Notifications contain device state updates (power, brightness, color, etc.)
        sent by the device in response to queries or spontaneously when state changes.

        Args:
            frame: Raw notification data received from the device.

        Returns:
            A dictionary containing parsed state values, or None if the packet
            is invalid or cannot be parsed. Common keys include:
            - "power": bool (True=on, False=off)
            - "brightness": int (0-255)
            - "color_rgb": tuple[int, int, int] (R, G, B)
            - "color_temp": int (Kelvin)
        """
        pass

    @abstractmethod
    def get_poll_commands(self) -> list[int]:
        """Return command IDs to query during polling.

        Returns:
            A list of command byte values to query for device state.
            For example, [0x01, 0x04, 0x05] to query power, brightness, and color.
        """
        pass
