"""Protocol abstraction layer for multi-model Govee BLE support.

This module implements a composition-based architecture where:
- GoveeProtocol: Abstract base defining the protocol interface
- Concrete protocol classes (H6006Protocol, etc.): Model-specific implementations
- ModelRegistry: Maps discovery names to protocol classes

Architecture rationale (from PROTOCOL_COMPARISON.md):
All H60xx models share the same core BLE protocol (20-byte packets, XOR checksum,
identical command bytes for power/brightness/RGB). The only differences are:
1. Capability flags (color temp support, music sync, etc.)
2. Discovery prefixes (ihoment_H6006, ihoment_H6008, etc.)
3. Model-specific advanced features (H6009 music sync/scenes)

This composition pattern maximizes code reuse while maintaining type safety and
clear capability boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

_PACKET_LEN = 20
_CMD_HEAD = 0x33


def _build_frame(cmd: int, payload: list[int]) -> bytes:
    """Build a 20-byte command packet for the Govee BLE protocol.

    This packet builder is shared across all H60xx models as they use
    identical packet structure (head 0x33, XOR checksum, 20 bytes total).

    Args:
        cmd: The command byte (e.g., 0x01 for power).
        payload: A list of bytes for the command payload.

    Returns:
        A 20-byte packet with XOR checksum in the final byte.
    """
    frame = [_CMD_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)


class GoveeProtocol(ABC):
    """Abstract base class for Govee BLE protocols.

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


class H6006Protocol(GoveeProtocol):
    """Protocol for Govee H6006 (RGBWW, 800 lm, 9W).

    Hardware-verified protocol. All other models derive from this baseline.
    """

    MODEL_NAME = "H6006"
    DISCOVERY_PREFIX = "ihoment_H6006"
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
        """
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).
        """
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).
        """
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Args:
            kelvin: Color temperature in Kelvin (2700-6500).

        Returns:
            20-byte BLE command packet.
        """
        kelvin = max(H6006Protocol.MIN_KELVIN, min(H6006Protocol.MAX_KELVIN, kelvin))
        warm = round(
            (H6006Protocol.MAX_KELVIN - kelvin)
            / (H6006Protocol.MAX_KELVIN - H6006Protocol.MIN_KELVIN)
            * 255
        )
        cold = 255 - warm
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])


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
        """
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).
        """
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).
        """
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame(0x05, [0x02, r, g, b])

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
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])


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
        """
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet.

        Args:
            value: Brightness level (0-255).
        """
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet.

        Args:
            r: Red intensity (0-255).
            g: Green intensity (0-255).
            b: Blue intensity (0-255).
        """
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame(0x05, [0x02, r, g, b])

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
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])


class ModelRegistry:
    """Registry mapping BLE discovery names to protocol classes.

    This registry is the single source of truth for:
    - Which models are supported
    - How to detect them via BLE advertising names
    - Which protocol implementation to use for each model

    Usage:
        # In config flow
        for prefix, protocol in ModelRegistry.get_all():
            if device.name.startswith(prefix):
                return protocol

        # In API
        protocol = ModelRegistry.get_protocol("ihoment_H6006_1234")
        api = GoveeAPI(device, protocol)
    """

    _REGISTRY: ClassVar[dict[str, type[GoveeProtocol]]] = {
        "ihoment_H6006": H6006Protocol,
        "ihoment_H6008": H6008Protocol,
        "ihoment_H6009": H6009Protocol,
    }

    @classmethod
    def get_protocol(cls, device_name: str) -> type[GoveeProtocol] | None:
        """Get protocol class for a BLE device name.

        Args:
            device_name: BLE advertising name (e.g., "ihoment_H6006_1234")

        Returns:
            Protocol class if matched, None otherwise.
        """
        for prefix, protocol in cls._REGISTRY.items():
            if device_name.startswith(prefix):
                return protocol
        return None

    @classmethod
    def get_all(cls) -> list[tuple[str, type[GoveeProtocol]]]:
        """Get all registered models as (prefix, protocol) tuples.

        Returns:
            List of (discovery_prefix, protocol_class) tuples.
        """
        return list(cls._REGISTRY.items())

    @classmethod
    def get_prefixes(cls) -> list[str]:
        """Get all discovery prefixes for manifest.json bluetooth field.

        Returns:
            List of BLE advertising name prefixes.
        """
        return list(cls._REGISTRY.keys())
