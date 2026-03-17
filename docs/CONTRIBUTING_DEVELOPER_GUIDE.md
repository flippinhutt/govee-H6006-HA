# Developer Guide: Adding Support for New Govee Models

This guide walks you through the process of adding support for a new Govee BLE device to this integration. It assumes you have:

- A Govee BLE device you want to add support for
- Basic knowledge of Bluetooth Low Energy (BLE) concepts
- Familiarity with Python and Home Assistant custom integrations
- Ability to reverse engineer BLE protocols (see [BLE Protocol Sniffing Tutorial](BLE_PROTOCOL_SNIFFING.md))

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Reverse Engineer the BLE Protocol](#step-1-reverse-engineer-the-ble-protocol)
- [Step 2: Create Model-Specific Packet Builders](#step-2-create-model-specific-packet-builders)
- [Step 3: Update Discovery and Config Flow](#step-3-update-discovery-and-config-flow)
- [Step 4: Add Model Detection Logic](#step-4-add-model-detection-logic)
- [Step 5: Update API and Coordinator](#step-5-update-api-and-coordinator)
- [Step 6: Write Tests](#step-6-write-tests)
- [Step 7: Validate with Real Hardware](#step-7-validate-with-real-hardware)
- [Step 8: Submit Your Contribution](#step-8-submit-your-contribution)
- [Troubleshooting](#troubleshooting)
- [Reference: H6006 Protocol Analysis](#reference-h6006-protocol-analysis)

## Overview

The integration architecture is designed to support multiple Govee models. Currently, it supports the H6006 model, but the codebase can be extended to handle other models with different BLE protocols.

### Current Architecture

```
custom_components/govee_h6006/
├── api_utils.py      # Packet builders (model-specific)
├── api.py            # BLE communication (shared)
├── coordinator.py    # State management (shared)
├── config_flow.py    # Discovery and setup (model detection)
├── light.py          # Home Assistant entity (shared)
└── const.py          # Constants and UUIDs
```

### Adding a New Model: High-Level Steps

1. **Reverse engineer** the BLE protocol for your device
2. **Create packet builders** for your model's command format
3. **Update config flow** to detect and configure your model
4. **Implement model detection** logic to route commands correctly
5. **Write tests** for your new model
6. **Validate** with real hardware
7. **Submit** a pull request

## Prerequisites

### Hardware

- The Govee BLE device you want to add support for
- A Bluetooth-enabled computer or Raspberry Pi for packet sniffing
- (Optional) A second Android/iOS device running the official Govee app

### Software

- **nRF Connect** (mobile app) or **Wireshark** with Bluetooth monitor
- Python 3.11+ with development tools installed
- Home Assistant instance for testing (can be a dev container)

### Knowledge

- BLE concepts: GATT, characteristics, UUIDs, advertising
- Python async programming
- Home Assistant integration patterns
- Basic reverse engineering skills

## Step 1: Reverse Engineer the BLE Protocol

Before you can add support for a new model, you need to understand its BLE protocol. This involves capturing and analyzing Bluetooth packets sent between the official Govee app and your device.

### 1.1 Identify Device Characteristics

Use **nRF Connect** (mobile) or **bluetoothctl** (Linux) to scan for your device:

```bash
# Linux: Use bluetoothctl
bluetoothctl
scan on
# Look for devices starting with "ihoment_" or "Govee_"
```

**Record:**
- Device name prefix (e.g., `ihoment_H7021_ABCD`)
- MAC address
- Advertised services and characteristics

### 1.2 Discover GATT Characteristics

Connect to the device and enumerate all GATT services and characteristics:

```bash
# Using nRF Connect app:
# 1. Connect to your device
# 2. Tap on each service to expand characteristics
# 3. Note the UUIDs for READ and WRITE characteristics
```

**For H6006, the UUIDs are:**
- Write characteristic: `00010203-0405-0607-0809-0a0b0c0d2b11`
- Read characteristic (notifications): `00010203-0405-0607-0809-0a0b0c0d2b10`

**Your device may use different UUIDs** — record them carefully.

### 1.3 Capture Bluetooth Packets

Use one of the following methods to capture packets:

#### Method A: nRF Connect Packet Logger (Recommended for beginners)

1. Install **nRF Connect** on your mobile device
2. Enable **logging** in app settings
3. Connect to your Govee device
4. Control the device (turn on/off, change color, etc.)
5. Export the log and analyze it

#### Method B: Wireshark + Bluetooth Monitor (Advanced)

On Linux with BlueZ:

```bash
# Start Bluetooth monitor
sudo btmon -w capture.log

# In another terminal, use bluetoothctl or the Govee app to control the device
bluetoothctl
connect XX:XX:XX:XX:XX:XX

# Stop btmon when done (Ctrl+C)
```

Open `capture.log` in Wireshark and filter for GATT writes:

```
bthci_acl.dst.bd_addr == XX:XX:XX:XX:XX:XX && btatt
```

#### Method C: Govee App + Packet Sniffer

Use the official Govee app on Android with **HCI snoop log** enabled:

1. Enable Developer Options on Android
2. Enable "Bluetooth HCI snoop log"
3. Control your device with the Govee app
4. Pull the log file: `adb pull /sdcard/Android/data/btsnoop_hci.log`
5. Open in Wireshark

### 1.4 Analyze Packet Structure

For each captured command (power on/off, brightness, color), identify:

- **Packet length** (H6006 uses 20 bytes)
- **Header/head byte** (H6006 uses `0x33` for commands, `0xAA` for queries)
- **Command byte** (e.g., `0x01` = power, `0x04` = brightness, `0x05` = color)
- **Payload format** (varies by command)
- **Checksum algorithm** (H6006 uses XOR of all bytes except the last)

**Example: H6006 Power On Command**

```
Hex: 33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33
     ├─ ├─ ├─ └─────────── padding (zeros) ──────────────────┘ ├─
     │  │  │                                                     │
     │  │  └─ payload (0x01 = on)                               │
     │  └─ command (0x01 = power)                               │
     └─ head (0x33)                                              └─ checksum (XOR)
```

**Document your findings:**
- Create a table of all commands and their packet formats
- Note any differences from H6006 (different head byte, checksum, etc.)
- Identify supported features (RGB, white mode, effects, etc.)

## Step 2: Create Model-Specific Packet Builders

Once you understand the protocol, create packet builder methods for your model.

### 2.1 Decide on Architecture Approach

You have two options:

#### Option A: Extend Existing `GoveePacket` Class (Simple, same protocol)

If your device uses the same protocol as H6006 (20-byte packets, XOR checksum, same command bytes), just use the existing `GoveePacket` class as-is.

#### Option B: Create Model-Specific Packet Builder (Different protocol)

If your device uses a different protocol, create a new packet builder class.

**Example: Create `api_utils_h7021.py` for H7021 model:**

```python
from __future__ import annotations

_PACKET_LEN = 20
_CMD_HEAD = 0x34  # Different head byte for H7021

def _build_frame_h7021(cmd: int, payload: list[int]) -> bytes:
    """Build a 20-byte command packet for Govee H7021.

    Args:
        cmd: The command byte.
        payload: A list of bytes for the command payload.

    Returns:
        A 20-byte packet with checksum in the final byte.
    """
    frame = [_CMD_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))
    # H7021 uses different checksum: sum of all bytes modulo 256
    checksum = sum(frame) & 0xFF
    frame.append(checksum)
    return bytes(frame)


class GoveeH7021Packet:
    """Packet builder for Govee H7021 BLE commands."""

    @staticmethod
    def power(on: bool) -> bytes:
        """Build a power command packet."""
        return _build_frame_h7021(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet."""
        value = max(0, min(255, value))
        return _build_frame_h7021(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet."""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame_h7021(0x05, [0x02, r, g, b])

    # Add more methods as needed for your device's features
```

### 2.2 Add Constants for Your Model

Update `const.py` with model-specific constants:

```python
# In const.py

# H6006 constants (existing)
H6006_WRITE_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
H6006_READ_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"
H6006_DISCOVERY_PREFIX = "ihoment_"

# H7021 constants (new)
H7021_WRITE_UUID = "00010203-0405-0607-0809-0a0b0c0d3b11"
H7021_READ_UUID = "00010203-0405-0607-0809-0a0b0c0d3b10"
H7021_DISCOVERY_PREFIX = "Govee_H7021_"
H7021_MIN_KELVIN = 2000
H7021_MAX_KELVIN = 9000
```

## Step 3: Update Discovery and Config Flow

The config flow needs to detect your new model during Bluetooth discovery.

### 3.1 Update Discovery Logic

Edit `config_flow.py` to recognize your device:

```python
# In config_flow.py

from .const import (
    DISCOVERY_NAME,
    H6006_DISCOVERY_PREFIX,  # existing
    H7021_DISCOVERY_PREFIX,  # new
)

async def async_step_user(
    self, user_input: dict[str, Any] | None = None
) -> dict:
    """Handle a flow initialized by the user via manual addition."""
    if user_input is not None:
        address = user_input["address"]
        self._discovery_info = self._discovered_devices[address]
        return await self.async_step_bluetooth_confirm()

    current_addresses = self._async_current_ids()
    for info in async_discovered_service_info(self.hass, connectable=True):
        if info.address in current_addresses or info.address in self._discovered_devices:
            continue
        # Support both H6006 and H7021 prefixes
        if not (info.name.startswith(H6006_DISCOVERY_PREFIX) or
                info.name.startswith(H7021_DISCOVERY_PREFIX)):
            continue
        self._discovered_devices[info.address] = info

    # ... rest of method
```

### 3.2 Store Model Information in Config Entry

When creating the config entry, store the detected model:

```python
# In config_flow.py, async_step_bluetooth_confirm method

def _detect_model(self, name: str) -> str:
    """Detect device model from name."""
    if name.startswith(H6006_DISCOVERY_PREFIX):
        return "H6006"
    elif name.startswith(H7021_DISCOVERY_PREFIX):
        return "H7021"
    return "unknown"

async def async_step_bluetooth_confirm(
    self, user_input: dict[str, Any] | None = None
) -> dict:
    """Confirm a device found via bluetooth discovery."""
    if self._discovery_info is None:
        return self.async_abort(reason="no_devices_found")

    if user_input is not None:
        model = self._detect_model(self._discovery_info.name)
        return self.async_create_entry(
            title=self._discovery_info.name,
            data={
                "address": self._discovery_info.address,
                "name": self._discovery_info.name,
                "model": model,  # Store model in config entry
            },
        )
    # ... rest of method
```

## Step 4: Add Model Detection Logic

Create a model registry to route commands to the correct packet builder.

### 4.1 Create a Model Registry (New File)

Create `custom_components/govee_h6006/models.py`:

```python
"""Model detection and packet builder registry for Govee devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .api_utils import GoveePacket
from .const import (
    H6006_MAX_KELVIN,
    H6006_MIN_KELVIN,
    H6006_READ_UUID,
    H6006_WRITE_UUID,
)

# Import your new model's packet builder
# from .api_utils_h7021 import GoveeH7021Packet


class PacketBuilder(Protocol):
    """Protocol for model-specific packet builders."""

    @staticmethod
    def power(on: bool) -> bytes:
        """Build a power command packet."""
        ...

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet."""
        ...

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet."""
        ...

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet."""
        ...


@dataclass
class ModelInfo:
    """Information about a Govee device model."""

    model_id: str
    name: str
    packet_builder: type[PacketBuilder]
    write_uuid: str
    read_uuid: str
    min_kelvin: int
    max_kelvin: int
    supports_rgb: bool = True
    supports_color_temp: bool = True


# Model registry
MODELS: dict[str, ModelInfo] = {
    "H6006": ModelInfo(
        model_id="H6006",
        name="Govee H6006 BLE Bulb",
        packet_builder=GoveePacket,
        write_uuid=H6006_WRITE_UUID,
        read_uuid=H6006_READ_UUID,
        min_kelvin=H6006_MIN_KELVIN,
        max_kelvin=H6006_MAX_KELVIN,
    ),
    # Add your new model here:
    # "H7021": ModelInfo(
    #     model_id="H7021",
    #     name="Govee H7021 LED Strip",
    #     packet_builder=GoveeH7021Packet,
    #     write_uuid=H7021_WRITE_UUID,
    #     read_uuid=H7021_READ_UUID,
    #     min_kelvin=H7021_MIN_KELVIN,
    #     max_kelvin=H7021_MAX_KELVIN,
    # ),
}


def get_model_info(model_id: str) -> ModelInfo:
    """Get model info by model ID.

    Args:
        model_id: The model identifier (e.g., "H6006").

    Returns:
        ModelInfo for the given model.

    Raises:
        ValueError: If model is not supported.
    """
    if model_id not in MODELS:
        raise ValueError(f"Unsupported model: {model_id}")
    return MODELS[model_id]
```

### 4.2 Update API to Use Model Info

Modify `api.py` to accept model info and use the correct packet builder:

```python
# In api.py

from .models import ModelInfo

class GoveeAPI:
    """Interface for Govee BLE device communication."""

    def __init__(
        self,
        ble_device: BLEDevice,
        model_info: ModelInfo,  # NEW: Accept model info
        update_callback: Callable[[], Awaitable[None]],
        timeout: float = 20.0,
        max_attempts: int = 5,
        suppression_window: int = 500,
    ) -> None:
        """Initialize the Govee API client."""
        self._ble_device = ble_device
        self._model_info = model_info  # NEW: Store model info
        self._update_callback = update_callback
        self._timeout = timeout
        # ... rest of init

    async def set_power(self, on: bool) -> None:
        """Set the power state of the device."""
        _LOGGER.debug(f"Sending power command: on={on}")
        # Use model-specific packet builder
        packet = self._model_info.packet_builder.power(on)
        await self._write(packet)

    async def set_brightness(self, value: int) -> None:
        """Set the brightness level of the device."""
        _LOGGER.debug(f"Sending brightness command: value={value}")
        packet = self._model_info.packet_builder.brightness(value)
        await self._write(packet)

    # Update other methods similarly...
```

### 4.3 Update Coordinator to Pass Model Info

Modify `coordinator.py` to get model info from the config entry:

```python
# In coordinator.py

from .models import get_model_info

class GoveeCoordinator(DataUpdateCoordinator[GoveeData]):
    """Data update coordinator for Govee BLE devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        ble_device: BLEDevice,
    ) -> None:
        """Initialize the coordinator."""
        # Get model info from config entry
        model_id = entry.data.get("model", "H6006")
        self._model_info = get_model_info(model_id)

        # ... rest of init

        self.api = GoveeAPI(
            ble_device=ble_device,
            model_info=self._model_info,  # Pass to API
            update_callback=self._handle_device_update,
            # ... other params
        )
```

## Step 5: Update API and Coordinator

If your model requires changes to notification handling or state parsing, update the API accordingly.

### 5.1 Update Notification Parser (if needed)

If your device sends notifications in a different format, modify `_handle_notification` in `api.py`:

```python
async def _handle_notification(
    self, characteristic: BleakGATTCharacteristic | None, frame: bytearray
) -> None:
    """Handle notification from device."""
    # Validate checksum (model-specific)
    if not self._validate_checksum(frame):
        _LOGGER.warning("Received packet with bad checksum, discarding")
        return

    # Parse based on model
    if self._model_info.model_id == "H6006":
        await self._parse_h6006_notification(frame)
    elif self._model_info.model_id == "H7021":
        await self._parse_h7021_notification(frame)
    # ... add more models

def _validate_checksum(self, frame: bytearray) -> bool:
    """Validate packet checksum (model-specific)."""
    if len(frame) < 20:
        return False

    if self._model_info.model_id == "H6006":
        # XOR checksum
        xor = 0
        for b in frame[:19]:
            xor ^= b
        return (xor & 0xFF) == frame[19]
    elif self._model_info.model_id == "H7021":
        # Sum checksum
        checksum = sum(frame[:19]) & 0xFF
        return checksum == frame[19]
    return False
```

### 5.2 Update State Query Commands (if needed)

If your device uses different query commands, update `poll_state()`:

```python
async def poll_state(self) -> None:
    """Request current state from device."""
    await self._ensure_connected()
    assert self._client is not None

    _LOGGER.debug("Polling device state")

    # Use model-specific query builder
    if self._model_info.model_id == "H6006":
        queries = [
            _build_query(_POWER_CMD),
            _build_query(_BRIGHTNESS_CMD),
            _build_query(_COLOR_CMD),
        ]
    elif self._model_info.model_id == "H7021":
        # H7021 might use a single state query
        queries = [_build_h7021_state_query()]

    for query in queries:
        await self._client.write_gatt_char(
            self._model_info.write_uuid, query, False
        )

    self.last_poll_time = time.time()
```

## Step 6: Write Tests

All new functionality must include comprehensive tests.

### 6.1 Create Test File for Your Model

Create `tests/test_api_h7021.py` (or similar):

```python
"""Tests for H7021 packet builders."""

import pytest

from custom_components.govee_h6006.api_utils_h7021 import GoveeH7021Packet


def test_h7021_power_on():
    """Test H7021 power on command."""
    packet = GoveeH7021Packet.power(True)
    assert len(packet) == 20
    assert packet[0] == 0x34  # H7021 head byte
    assert packet[1] == 0x01  # Power command
    assert packet[2] == 0x01  # On
    # Validate checksum (sum)
    expected_checksum = sum(packet[:19]) & 0xFF
    assert packet[19] == expected_checksum


def test_h7021_power_off():
    """Test H7021 power off command."""
    packet = GoveeH7021Packet.power(False)
    assert len(packet) == 20
    assert packet[0] == 0x34
    assert packet[1] == 0x01
    assert packet[2] == 0x00  # Off


def test_h7021_brightness():
    """Test H7021 brightness command."""
    packet = GoveeH7021Packet.brightness(128)
    assert len(packet) == 20
    assert packet[0] == 0x34
    assert packet[1] == 0x04
    assert packet[2] == 128


def test_h7021_color_rgb():
    """Test H7021 RGB color command."""
    packet = GoveeH7021Packet.color_rgb(255, 128, 64)
    assert len(packet) == 20
    assert packet[0] == 0x34
    assert packet[1] == 0x05
    assert packet[3] == 255  # R
    assert packet[4] == 128  # G
    assert packet[5] == 64   # B
```

### 6.2 Update Config Flow Tests

Add tests for discovering your new model in `tests/test_config_flow.py`:

```python
async def test_user_flow_h7021(hass, mock_bluetooth_discovery_h7021):
    """Test user config flow for H7021 device."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"

    # User selects the H7021 device
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "AA:BB:CC:DD:EE:FF"},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "bluetooth_confirm"

    # User confirms
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == "create_entry"
    assert result["data"]["model"] == "H7021"
```

### 6.3 Run Tests

```bash
# Run all tests
pytest

# Run tests for your new model
pytest -k "h7021"

# Check coverage
pytest --cov=custom_components/govee_h6006 --cov-report=term-missing
```

**Aim for 90%+ coverage on all new code.**

## Step 7: Validate with Real Hardware

Before submitting your contribution, test with the actual device.

### 7.1 Install Your Modified Integration

Copy your modified integration to your Home Assistant config:

```bash
# From your development directory
cp -r custom_components/govee_h6006 /path/to/homeassistant/config/custom_components/
```

### 7.2 Restart Home Assistant

```bash
# Via Home Assistant UI: Settings → System → Restart
# Or via CLI:
ha core restart
```

### 7.3 Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.govee_h6006: debug
    bleak: debug
```

### 7.4 Test All Functionality

Create a checklist and test each feature:

- [ ] Device is discovered automatically
- [ ] Manual setup works
- [ ] Device can be turned on/off
- [ ] Brightness can be adjusted (0-100%)
- [ ] RGB color can be changed
- [ ] Color temperature can be changed (if supported)
- [ ] State updates are reflected in UI
- [ ] Device reconnects after connection loss
- [ ] Multiple devices can be added (if you have more than one)

### 7.5 Check Logs for Errors

```bash
# View live logs
tail -f /config/home-assistant.log | grep govee

# Look for:
# - Connection errors
# - Packet parse errors
# - Unexpected disconnections
```

### 7.6 Test Edge Cases

- Rapidly toggle power on/off (test optimistic updates)
- Turn off Bluetooth adapter and turn it back on (test reconnection)
- Control device via Govee app while HA is connected (test state sync)
- Restart Home Assistant while device is on (test state recovery)

## Step 8: Submit Your Contribution

Once testing is complete, submit your changes.

### 8.1 Update Documentation

Before submitting, update all relevant documentation:

**1. Update README.md**

Add your model to the supported devices list:

```markdown
## Supported Devices

- **H6006** - Govee Color Bulb (BLE)
- **H7021** - Govee LED Strip (NEW)
```

**2. Update CHANGELOG.md**

```markdown
## [Unreleased]

### Added
- Support for Govee H7021 LED Strip (@your-github-username)
```

**3. Update CLAUDE.md**

Add any architectural changes or new patterns:

```markdown
## Supported Models

- H6006: Original bulb, XOR checksum, 2700-6500K range
- H7021: LED strip, sum checksum, 2000-9000K range, uses 0x34 head byte
```

**4. Add Model-Specific Documentation (Optional)**

Create `docs/models/H7021.md` with device-specific notes:

```markdown
# Govee H7021 LED Strip

## BLE Protocol

- **Head Byte:** 0x34
- **Checksum:** Sum of bytes 0-18, modulo 256
- **UUIDs:**
  - Write: `00010203-0405-0607-0809-0a0b0c0d3b11`
  - Read: `00010203-0405-0607-0809-0a0b0c0d3b10`

## Supported Features

- RGB color
- Color temperature (2000K - 9000K)
- Brightness (0-255)
- Power on/off

## Known Issues

- None
```

### 8.2 Run Final Checks

```bash
# All tests pass
pytest

# Code passes linting
ruff check .
ruff format .

# Type checking passes
mypy custom_components/govee_h6006

# Coverage is maintained
pytest --cov=custom_components/govee_h6006 --cov-report=term-missing
```

### 8.3 Commit Your Changes

```bash
git add .
git commit -m "Add support for Govee H7021 LED Strip

- Add H7021 packet builder with sum checksum
- Update config flow to detect H7021 devices
- Add model registry and routing logic
- Add comprehensive tests for H7021
- Update documentation

Tested with real H7021 hardware."
```

### 8.4 Open a Pull Request

1. Push your branch: `git push origin feature/add-h7021-support`
2. Open a PR on GitHub
3. Fill out the PR template with:
   - **Description:** What device you added and why
   - **Testing:** Hardware testing notes and logs
   - **BLE Protocol:** Summary of protocol differences from H6006
   - **Screenshots:** (Optional) Screenshots of device in Home Assistant UI

**Example PR Description:**

```markdown
## Add Support for Govee H7021 LED Strip

This PR adds support for the Govee H7021 BLE LED Strip.

### Changes

- Created `api_utils_h7021.py` with H7021-specific packet builder
- Updated config flow to detect H7021 devices (prefix: `Govee_H7021_`)
- Added model registry (`models.py`) to route commands based on device model
- Updated API to use model-specific packet builders and UUIDs
- Added comprehensive tests (95% coverage on new code)

### Protocol Differences from H6006

| Feature | H6006 | H7021 |
|---------|-------|-------|
| Head byte | 0x33 | 0x34 |
| Checksum | XOR | Sum (mod 256) |
| Write UUID | ...2b11 | ...3b11 |
| Read UUID | ...2b10 | ...3b10 |
| Kelvin range | 2700-6500 | 2000-9000 |

### Testing

Tested with real H7021 hardware:
- [x] Discovery works
- [x] Power on/off
- [x] Brightness adjustment
- [x] RGB color changes
- [x] Color temperature changes
- [x] Reconnection after BLE loss
- [x] State sync with Govee app

### Screenshots

(attach screenshots here)

### Checklist

- [x] All tests pass
- [x] Code passes linting
- [x] Type checking passes
- [x] Documentation updated
- [x] Hardware tested
```

## Troubleshooting

### Issue: Device not discovered

**Possible causes:**
- Device name prefix doesn't match
- Device is not advertising as connectable
- Another app/integration has an active connection

**Solutions:**
1. Check device name with `bluetoothctl scan on`
2. Update discovery prefix in `const.py`
3. Disable other Bluetooth connections to the device
4. Restart Home Assistant Bluetooth integration

### Issue: Connection timeout

**Possible causes:**
- Incorrect UUIDs
- Device requires pairing
- Bluetooth adapter issue

**Solutions:**
1. Verify UUIDs with nRF Connect
2. Try manual pairing: `bluetoothctl pair XX:XX:XX:XX:XX:XX`
3. Increase connection timeout in options
4. Check Bluetooth adapter proximity/signal strength

### Issue: Commands not working

**Possible causes:**
- Incorrect packet format
- Wrong checksum algorithm
- Incorrect characteristic UUID

**Solutions:**
1. Re-capture packets and verify format
2. Test checksum calculation with known packets
3. Log outgoing packets and compare with captures:
   ```python
   _LOGGER.debug(f"Sending packet: {packet.hex()}")
   ```

### Issue: State not updating

**Possible causes:**
- Notification parsing error
- Incorrect read characteristic UUID
- Notifications not enabled

**Solutions:**
1. Enable debug logging and check for parse errors
2. Verify read UUID matches device GATT services
3. Check that `start_notify()` is called on the correct UUID

### Issue: Tests failing

**Possible causes:**
- Mock setup incorrect
- Test assumptions don't match new model
- Import errors

**Solutions:**
1. Check `conftest.py` has mocks for your new modules
2. Update test fixtures for new model
3. Run pytest with `-v` flag for detailed output

## Reference: H6006 Protocol Analysis

This section documents the complete H6006 protocol as a reference for adding new models.

### Packet Structure

**All packets are 20 bytes:**

```
Bytes 0-18: Header + Command + Payload (padded with zeros)
Byte 19:    XOR checksum of bytes 0-18
```

### Command Packets (Head 0x33)

| Command | Byte 0 | Byte 1 | Bytes 2-18 | Byte 19 |
|---------|--------|--------|------------|---------|
| Power On | 0x33 | 0x01 | 0x01, 0x00... | XOR |
| Power Off | 0x33 | 0x01 | 0x00, 0x00... | XOR |
| Brightness | 0x33 | 0x04 | value (0-255), 0x00... | XOR |
| RGB Color | 0x33 | 0x05 | 0x02, R, G, B, 0x00... | XOR |
| Color Temp | 0x33 | 0x05 | 0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold, 0x00... | XOR |

### Query Packets (Head 0xAA)

| Query | Byte 0 | Byte 1 | Bytes 2-18 | Byte 19 |
|-------|--------|--------|------------|---------|
| Power | 0xAA | 0x01 | 0x00... | XOR |
| Brightness | 0xAA | 0x04 | 0x00... | XOR |
| Color | 0xAA | 0x05 | 0x00... | XOR |

### Response Packets (Head 0xAA)

Same format as query packets, but with state data in bytes 2+.

### Color Temperature Calculation

```python
# Kelvin to warm/cold bytes (sum to 255)
warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
cold = 255 - warm

# Warm/cold bytes to Kelvin
kelvin = round(MAX_KELVIN - (warm / 255) * (MAX_KELVIN - MIN_KELVIN))
```

### Checksum Calculation (XOR)

```python
checksum = 0
for byte in packet[0:19]:
    checksum ^= byte
checksum &= 0xFF
```

### GATT Characteristics

- **Service UUID:** (device-specific, check with nRF Connect)
- **Write Characteristic:** `00010203-0405-0607-0809-0a0b0c0d2b11`
- **Read Characteristic (Notify):** `00010203-0405-0607-0809-0a0b0c0d2b10`

---

## Questions?

If you run into issues or have questions:

1. **Search existing issues** on GitHub
2. **Post in GitHub Discussions** (Q&A category)
3. **Open a Device Support Request** issue with your BLE captures

Happy coding! 🎉
