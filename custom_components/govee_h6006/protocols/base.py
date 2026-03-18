"""Base protocol abstraction for Govee BLE devices."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar


class GoveeProtocol(ABC):
    """Abstract base class for Govee BLE device protocols.

    Defines the interface that all protocol implementations must provide,
    along with capability flags that control feature availability.

    Attributes:
        MODEL_NAME: Human-readable model name (e.g., "H6006")
        DISCOVERY_PREFIX: BLE advertising name prefix (e.g., "ihoment_H6006")
        HAS_COLOR_TEMP: Whether model supports color temperature control
        HAS_MUSIC_SYNC: Whether model supports music sync mode (H6009)
        HAS_SCENE_MODES: Whether model supports preset scene modes (H6009)
        MIN_KELVIN: Minimum color temperature in Kelvin (if HAS_COLOR_TEMP)
        MAX_KELVIN: Maximum color temperature in Kelvin (if HAS_COLOR_TEMP)
    """

    MODEL_NAME: ClassVar[str]
    DISCOVERY_PREFIX: ClassVar[str]
    HAS_COLOR_TEMP: ClassVar[bool] = False
    HAS_MUSIC_SYNC: ClassVar[bool] = False
    HAS_SCENE_MODES: ClassVar[bool] = False
    MIN_KELVIN: ClassVar[int] = 2700
    MAX_KELVIN: ClassVar[int] = 6500

    @staticmethod
    @abstractmethod
    def power(on: bool) -> bytes:
        """Build a power command packet.

        Args:
            on: True for turn on, False for turn off.

        Returns:
            20-byte BLE command packet.
        """

    @staticmethod
    @abstractmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).

        Returns:
            20-byte BLE command packet.
        """

    @staticmethod
    @abstractmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).

        Returns:
            20-byte BLE command packet.
        """


def build_frame(cmd: int, payload: list[int]) -> bytes:
    """Build a 20-byte command packet for the Govee BLE protocol.

    This packet builder is shared across all H60xx models as they use
    identical packet structure (head 0x33, XOR checksum, 20 bytes total).

    Args:
        cmd: The command byte (e.g., 0x01 for power).
        payload: A list of bytes for the command payload.

    Returns:
        A 20-byte packet with XOR checksum in the final byte.
    """
    _packet_len = 20
    _cmd_head = 0x33

    frame = [_cmd_head, cmd & 0xFF] + payload
    frame += [0] * (_packet_len - 1 - len(frame))
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)
