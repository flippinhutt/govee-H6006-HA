# Adding Support for New Govee Models

This guide explains how to extend the Govee H6006 integration to support additional Govee BLE device models using the pluggable protocol architecture.

## Overview of the Protocol Architecture

The integration uses a **pluggable protocol system** that separates device-specific packet encoding/decoding logic from the core BLE communication layer. This design makes it easy to support multiple Govee models with different BLE protocols without modifying the core integration code.

### Key Components

1. **`GoveeProtocol` (Abstract Base Class)**: Defines the interface that all protocol implementations must follow. Located in `custom_components/govee_h6006/protocols/base.py`.

2. **Protocol Implementations**: Concrete classes (e.g., `H6006Protocol`) that implement the abstract methods for building command packets and parsing notifications. Located in `custom_components/govee_h6006/protocols/`.

3. **Protocol Registry**: Maps device name prefixes to protocol classes, enabling automatic protocol selection based on BLE advertisement names. Located in `custom_components/govee_h6006/protocols/__init__.py`.

4. **`GoveeAPI`**: Uses a protocol instance to build commands and parse responses, but remains agnostic to protocol-specific details.

### Data Flow

```
User Command → GoveeLight → GoveeCoordinator → GoveeAPI
                                                   ↓
                                              Protocol.build_*_packet()
                                                   ↓
                                              BLE Write

BLE Notification → GoveeAPI → Protocol.parse_notification()
                       ↓
                  Coordinator Update → UI Refresh
```

## Step-by-Step Guide: Adding a New Model

Let's walk through adding support for a hypothetical **Govee H6008** model.

### Step 1: Reverse-Engineer the BLE Protocol

Before writing any code, you need to understand the device's BLE protocol:

1. **Identify BLE Characteristics**: Use a tool like `nRF Connect` (mobile) or `bluetoothctl` (Linux) to discover the device's GATT services and characteristics. Look for writable characteristics (for commands) and notifying characteristics (for state updates).

2. **Capture Packet Samples**: Sniff BLE traffic using the official Govee app while controlling the device. Tools:
   - **Android**: `nRF Connect` → Sniffer mode
   - **iOS**: Xcode Instruments → Bluetooth template
   - **Desktop**: Wireshark with BTLE capture

3. **Analyze Packet Structure**: Determine:
   - Packet length (e.g., 20 bytes)
   - Header byte(s) for commands vs. responses
   - Command byte values (e.g., `0x01` for power, `0x04` for brightness)
   - Payload encoding (e.g., RGB order, color temp calculation)
   - Checksum algorithm (e.g., XOR, CRC-8)

### Step 2: Create a New Protocol Class

Create a new file `custom_components/govee_h6006/protocols/h6008.py`:

```python
"""H6008 Protocol implementation for Govee H6008 BLE lights."""
from __future__ import annotations

import logging

from .base import GoveeProtocol
from ..const import MAX_KELVIN, MIN_KELVIN

_LOGGER = logging.getLogger(__name__)

# Protocol constants (adjust based on reverse-engineering)
_PACKET_LEN = 20
_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


class H6008Protocol(GoveeProtocol):
    """Protocol implementation for Govee H6008 lights.

    The H6008 uses a similar 20-byte BLE packet format to the H6006:
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
        """Build a 20-byte command packet for the H6008 BLE protocol.

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
        """Parse a notification packet from the H6008 device.

        The H6008 sends notifications (head=0xAA) when state changes or in response
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
            # Return empty dict for unknown commands (valid packet, but no state updates)
            # The API layer distinguishes between None (invalid) and {} (valid but unknown)
            return result
        except Exception as err:
            _LOGGER.error(f"Error parsing notification: {err}")
            return None

    def get_poll_commands(self) -> list[int]:
        """Return command IDs to query during polling.

        Returns:
            Command IDs for power, brightness, and color state queries.
        """
        return [_POWER_CMD, _BRIGHTNESS_CMD, _COLOR_CMD]
```

**Important Notes:**
- If the H6008 uses a **different packet structure** (e.g., 16 bytes instead of 20), adjust `_PACKET_LEN` and the `_build_frame` method accordingly.
- If the **checksum algorithm differs** (e.g., CRC-8 instead of XOR), replace the checksum logic in `_build_frame` and `parse_notification`.
- If the **command byte values differ**, update the `_POWER_CMD`, `_BRIGHTNESS_CMD`, etc., constants.
- **Always add debug logging** in `parse_notification` to help diagnose issues during testing.

### Step 3: Register the Protocol

Edit `custom_components/govee_h6006/protocols/__init__.py`:

```python
"""Govee BLE protocol abstractions."""
from __future__ import annotations

from typing import Type

from .base import GoveeProtocol
from .h6006 import H6006Protocol
from .h6008 import H6008Protocol  # Add this import

# Protocol registry: maps device name prefix to protocol class
_PROTOCOL_REGISTRY: dict[str, Type[GoveeProtocol]] = {
    "ihoment_": H6006Protocol,
    "govee_H6008_": H6008Protocol,  # Add this mapping
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


__all__ = ["GoveeProtocol", "H6006Protocol", "H6008Protocol", "get_protocol"]  # Add H6008Protocol
```

**Key Points:**
- The **device name prefix** must match the BLE advertisement name. Use `nRF Connect` or `hcitool lescan` to discover the exact prefix.
- The registry uses **prefix matching**, so `"govee_H6008_"` will match devices named `"govee_H6008_1234"`, `"govee_H6008_ABCD"`, etc.

### Step 4: Write Tests

Create `tests/protocols/test_h6008.py` to verify your protocol implementation:

```python
"""Tests for H6008 protocol implementation."""
import pytest
from custom_components.govee_h6006.protocols.h6008 import H6008Protocol


@pytest.fixture
def protocol():
    """Fixture to create an H6008Protocol instance."""
    return H6008Protocol()


def test_build_power_on(protocol):
    """Test power-on packet construction."""
    packet = protocol.build_power_packet(on=True)
    assert len(packet) == 20
    assert packet[0] == 0x33  # Command head
    assert packet[1] == 0x01  # Power command
    assert packet[2] == 0x01  # On


def test_build_power_off(protocol):
    """Test power-off packet construction."""
    packet = protocol.build_power_packet(on=False)
    assert packet[2] == 0x00  # Off


def test_build_brightness(protocol):
    """Test brightness packet construction."""
    packet = protocol.build_brightness_packet(128)
    assert packet[1] == 0x04  # Brightness command
    assert packet[2] == 128


def test_build_color_rgb(protocol):
    """Test RGB color packet construction."""
    packet = protocol.build_color_rgb_packet(255, 128, 64)
    assert packet[1] == 0x05  # Color command
    assert packet[2] == 0x02  # RGB mode
    assert packet[3] == 255  # Red
    assert packet[4] == 128  # Green
    assert packet[5] == 64   # Blue


def test_parse_power_notification(protocol):
    """Test parsing power state notification."""
    # Construct a valid notification packet
    frame = bytearray([0xAA, 0x01, 0x01] + [0] * 16)
    # Calculate checksum
    xor = 0
    for b in frame[:19]:
        xor ^= b
    frame.append(xor & 0xFF)

    result = protocol.parse_notification(frame)
    assert result is not None
    assert result.get("power") is True


def test_parse_invalid_checksum(protocol):
    """Test that invalid checksums are rejected."""
    frame = bytearray([0xAA, 0x01, 0x01] + [0] * 16 + [0xFF])  # Wrong checksum
    result = protocol.parse_notification(frame)
    assert result is None
```

Run the tests:

```bash
pytest tests/protocols/test_h6008.py -v
```

### Step 5: Update Configuration Flow (Optional)

If the H6008 uses a **different discovery prefix**, you may need to update the Bluetooth discovery filter in `config_flow.py`. However, if the device advertises with a prefix like `govee_H6008_`, the existing discovery flow should work automatically.

To verify discovery:
1. Enable debug logging in Home Assistant (`logger: custom_components.govee_h6006: debug`)
2. Restart Home Assistant
3. Check the logs for discovered BLE devices

### Step 6: Test with Real Hardware

1. **Pair the device**: Go to Home Assistant → Settings → Devices & Services → Add Integration → Govee H6006.
2. **Verify discovery**: The H6008 should appear in the device list if it's broadcasting.
3. **Test commands**: Turn on/off, adjust brightness, change colors.
4. **Monitor logs**: Check for any errors in the logs (Settings → System → Logs).

## Protocol Variations: Common Scenarios

### Scenario 1: Different Packet Length

If the H6008 uses 16-byte packets instead of 20:

```python
_PACKET_LEN = 16  # Update this constant

def _build_frame(self, cmd: int, payload: list[int]) -> bytes:
    frame = [self.COMMAND_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))  # Adjust padding
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)
```

### Scenario 2: Different Checksum Algorithm (CRC-8)

Replace the XOR checksum with CRC-8:

```python
def _crc8(data: list[int]) -> int:
    """Calculate CRC-8 checksum."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

def _build_frame(self, cmd: int, payload: list[int]) -> bytes:
    frame = [self.COMMAND_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))
    checksum = _crc8(frame)
    frame.append(checksum)
    return bytes(frame)
```

### Scenario 3: No Color Temperature Support

If the device doesn't support color temperature (white mode), raise an exception:

```python
def build_color_temp_packet(self, kelvin: int) -> bytes:
    """H6008 does not support color temperature."""
    raise NotImplementedError("H6008 does not support color temperature")
```

Then update `light.py` to check for this capability and exclude `COLOR_MODE_COLOR_TEMP` from supported modes.

### Scenario 4: Additional Commands (Effects, Music Mode)

If the device supports effects or music modes, add new abstract methods to `GoveeProtocol`:

```python
# In protocols/base.py
@abstractmethod
def build_effect_packet(self, effect_id: int) -> bytes:
    """Build an effect command packet."""
    pass
```

Then implement in `H6008Protocol`:

```python
_EFFECT_CMD = 0x06

def build_effect_packet(self, effect_id: int) -> bytes:
    """Build an effect command packet."""
    return self._build_frame(_EFFECT_CMD, [effect_id])
```

## Troubleshooting

### Problem: Device not discovered

**Solution**: Check the BLE advertisement name using `nRF Connect`. Verify that the prefix in `_PROTOCOL_REGISTRY` matches exactly.

### Problem: Commands don't work

**Solution**: Enable debug logging and compare the packets you're sending with those captured from the official Govee app. Common issues:
- Incorrect command byte values
- Wrong byte order (e.g., BGR instead of RGB)
- Missing or incorrect checksum

### Problem: Notifications not parsed

**Solution**: Check the notification handler logs. Common issues:
- Incorrect `REQUEST_HEAD` value
- Checksum verification failing
- Wrong byte offsets for state values

## Testing Checklist

Before submitting a pull request:

- [ ] Protocol class implements all abstract methods from `GoveeProtocol`
- [ ] Protocol is registered in `_PROTOCOL_REGISTRY` with correct prefix
- [ ] Unit tests cover all command builders and notification parsing
- [ ] Integration test with real hardware confirms basic functionality (on/off, brightness, color)
- [ ] Debug logs show correct packet structure
- [ ] Code follows existing style (ruff, mypy pass)
- [ ] Documentation updated (this file, README if needed)

## Further Reading

- [BLE Protocol Reverse Engineering Guide](https://github.com/NordicSemiconductor/Android-nRF-Connect/blob/main/README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall integration architecture
- [API.md](./API.md) - Internal API reference
- [Home Assistant BLE Integration Guide](https://developers.home-assistant.io/docs/device_integration_index/#bluetooth)

## Contributing

When you've successfully added support for a new model, please contribute it back to the project! Open a pull request with:
1. The new protocol implementation
2. Tests for the protocol
3. Update to this document listing the new model
4. Any changes to `const.py` (e.g., new device name prefixes)

Your contribution helps the community support more Govee devices! 🎉
