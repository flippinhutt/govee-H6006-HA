"""Govee BLE protocol abstractions."""
from __future__ import annotations

from typing import Type

from .base import GoveeProtocol
from .h6006 import H6006Protocol

# Protocol registry: maps device name prefix to protocol class
_PROTOCOL_REGISTRY: dict[str, Type[GoveeProtocol]] = {
    "ihoment_": H6006Protocol,
}


def get_protocol(device_name: str) -> GoveeProtocol:
    """Get the appropriate protocol instance for a device name.

    Protocol selection is based on matching device name prefixes registered
    in the protocol registry. This enables automatic protocol detection based
    on BLE device advertisement names.

    Args:
        device_name: The BLE device name (e.g., "ihoment_H6006_1234").

    Returns:
        An instance of the appropriate GoveeProtocol subclass.

    Raises:
        ValueError: If no registered protocol matches the device name.

    Example:
        >>> protocol = get_protocol("ihoment_H6006_1234")
        >>> isinstance(protocol, H6006Protocol)
        True
    """
    for prefix, protocol_class in _PROTOCOL_REGISTRY.items():
        if device_name.startswith(prefix):
            return protocol_class()

    raise ValueError(
        f"No protocol registered for device '{device_name}'. "
        f"Supported prefixes: {', '.join(_PROTOCOL_REGISTRY.keys())}"
    )


__all__ = ["GoveeProtocol", "H6006Protocol", "get_protocol"]
