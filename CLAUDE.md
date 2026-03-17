# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. ALWAYS update CLAUDE.md and CHANGELOG.md when changes are made. 

## Project

HACS custom integration for Govee H60xx series light bulbs (H6006, H6008, H6009, H6003). This integration uses **Bluetooth Low Energy (BLE) only** — not WiFi — for local-only control with zero cloud dependency. These devices support both BLE and WiFi, but we deliberately use BLE to avoid cloud connectivity requirements. Targets Home Assistant with `bleak` + `bleak-retry-connector` for BLE communication.

**Supported Models:**
- **H6006** (RGBWW, 800 lm, 9W) — Hardware-verified baseline
- **H6008** (RGBWW, 800 lm, 9W) — Protocol research verified
- **H6009** (RGBWW, 1200 lm, 12W) — Protocol research verified, music sync + scenes
- **H6003** (RGB, 800 lm, 9W) — Protocol research verified, RGB-only (no color temp)

Domain: `govee_h6006`. Discovery prefixes: `ihoment_H6006`, `ihoment_H6008`, `ihoment_H6009`, `ihoment_H6003`.

## Commands

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_api.py

# Stop on first failure
pytest -x

# Run tests matching a keyword
pytest -k "test_brightness"

# Run linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Run type checking
mypy custom_components/govee_h6006

# Type check a specific file
mypy custom_components/govee_h6006/api.py
```

No build step. No requirements.txt — dependencies are declared in `manifest.json` (`bleak-retry-connector>=3.0.0`). Tests stub out `bleak`, `bleak_retry_connector`, and all `homeassistant` modules via `tests/conftest.py` so no HA installation is needed to run tests.

## Pre-commit Hooks (Optional)

You can optionally set up pre-commit hooks to automatically run ruff and mypy before each commit:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# (Optional) Run against all files
pre-commit run --all-files
```

Create `.pre-commit-config.yaml` in the repository root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        files: ^custom_components/govee_h6006/
        args: [--ignore-missing-imports, --check-untyped-defs]
```

Once installed, ruff and mypy will run automatically on staged files before each commit. If issues are found, the commit will be blocked until they're resolved. You can bypass the hooks with `git commit --no-verify` if needed.

## Architecture

```
custom_components/govee_h6006/
├── protocols.py      # Protocol abstraction layer for multi-model support
├── api.py            # GoveeAPI — BLE connection, writes commands, parses notifications (head 0xAA)
├── coordinator.py    # GoveeCoordinator (DataUpdateCoordinator) — polls every 30s, proxies commands
├── config_flow.py    # Bluetooth discovery + manual user setup flow
├── light.py          # GoveeLight (LightEntity) — RGB + color temp modes
├── const.py          # UUIDs, domain, MODEL_REGISTRY, kelvin range
└── translations/     # UI strings
```

**Two packet heads:** Command frames use `0x33` (built by protocol classes in `protocols.py`). Query/response frames use `0xAA` (built/parsed in `api.py`). Both are 20 bytes with XOR checksum in the last byte.

**Data flow:** `LightEntity` -> `GoveeCoordinator` -> `GoveeAPI` -> Protocol class -> BLE write. Notifications flow back via `_handle_notification` callback -> `coordinator.async_set_updated_data`.

**Test stubs:** `conftest.py` patches `sys.modules` to stub all external dependencies (homeassistant, bleak, voluptuous). Tests run without any of these packages installed. The `_FlowManager` in conftest directly invokes config flow steps.

## Protocol Reference

| Command | Head | Cmd | Payload |
|---------|------|-----|---------|
| Power   | 0x33 | 0x01 | 0x01 (on) / 0x00 (off) |
| Brightness | 0x33 | 0x04 | 0-255 |
| RGB color | 0x33 | 0x05 | 0x02, R, G, B |
| Color temp | 0x33 | 0x05 | 0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold |

Color temp range: 2700K–6500K. Warm/cold bytes are complementary (sum to 255).

## Multi-Model Architecture

The integration uses a **composition-based protocol abstraction** to support multiple Govee models while maximizing code reuse:

### protocols.py — Protocol Abstraction Layer

**Architecture rationale:** All H60xx models share the same core BLE protocol (20-byte packets, XOR checksum, identical command bytes for power/brightness/RGB). The only differences are:
1. **Capability flags** (color temp support, music sync, scene modes)
2. **Discovery prefixes** (`ihoment_H6006`, `ihoment_H6008`, etc.)
3. **Model-specific advanced features** (H6009 music sync/scenes)

**Components:**
- `GoveeProtocol` (ABC) — Abstract base defining the protocol interface with capability flags (`HAS_COLOR_TEMP`, `HAS_MUSIC_SYNC`, `HAS_SCENE_MODES`)
- `H6006Protocol`, `H6008Protocol`, `H6009Protocol`, `H6003Protocol` — Concrete implementations
- `ModelRegistry` — Maps BLE discovery names to protocol classes
- `_build_frame()` — Shared 20-byte packet builder (used by all models)

**Capability flags control feature availability:**
```python
# H6006/H6008/H6009 support color temperature
HAS_COLOR_TEMP = True
MIN_KELVIN = 2700
MAX_KELVIN = 6500

# H6003 is RGB-only, no color temp
HAS_COLOR_TEMP = False

# H6009 has music sync and scene modes
HAS_MUSIC_SYNC = True
HAS_SCENE_MODES = True
```

**Protocol selection flow:**
1. BLE device discovered (e.g., `ihoment_H6008_1234`)
2. `ModelRegistry.get_protocol(device_name)` matches prefix → returns `H6008Protocol`
3. `GoveeAPI` instantiated with protocol class
4. All commands route through protocol's static methods (`power()`, `brightness()`, `color_rgb()`, etc.)

### const.py — MODEL_REGISTRY

`MODEL_REGISTRY` is the **single source of truth** for supported models. It maps model identifiers to metadata:
```python
MODEL_REGISTRY = {
    "H6006": {
        "name": "Govee H6006",
        "discovery_prefix": "ihoment_H6006",
        "write_uuid": "00010203-0405-0607-0809-0a0b0c0d2b11",
        "read_uuid": "00010203-0405-0607-0809-0a0b0c0d2b10",
        "min_kelvin": 2700,
        "max_kelvin": 6500,
        "protocol_class": "H6006Protocol",
        "capabilities": {
            "color_temp": True,
            "music_sync": False,
            "scene_modes": False,
        },
    },
    # ... H6008, H6009, H6003 ...
}
```

**Usage:**
- `config_flow.py` — Uses discovery prefixes for auto-detection
- `manifest.json` — Uses all prefixes for Bluetooth matcher
- `light.py` — Checks capabilities to determine supported color modes

### Adding New Models

To add support for a new Govee model (e.g., H6104), follow these steps:

**1. Protocol Research**

First, determine if the model uses the standard H60xx BLE protocol:
- Search GitHub/forums for existing protocol documentation (govee-reverse-engineering, govee2mqtt issues, etc.)
- Look for packet captures showing command structure
- Verify command bytes match the standard protocol:
  - Power: `0x33 0x01 [0x01/0x00]`
  - Brightness: `0x33 0x04 [0-255]`
  - RGB color: `0x33 0x05 0x02 [R] [G] [B]`
  - Color temp (if supported): `0x33 0x05 0x02 0xFF 0xFF 0xFF 0x01 [warm] [cold]`
- Confirm BLE UUIDs (write: `2b11`, read: `2b10`)
- Note discovery prefix pattern (usually `ihoment_H6104`)

**Key questions:**
- Does it support color temperature control? (RGBWW vs RGB-only)
- Does it have special features? (music sync, scene modes, etc.)
- What's the kelvin range? (usually 2700–6500K)

**2. Create Protocol Class** (`protocols.py`)

Add a new protocol class inheriting from `GoveeProtocol`:
```python
class H6104Protocol(GoveeProtocol):
    """Protocol for Govee H6104 (description here).

    Hardware verification status: pending/verified.
    """

    MODEL_NAME = "H6104"
    DISCOVERY_PREFIX = "ihoment_H6104"
    HAS_COLOR_TEMP = True  # or False for RGB-only
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False
    MIN_KELVIN = 2700
    MAX_KELVIN = 6500

    @staticmethod
    def power(on: bool) -> bytes:
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame(0x05, [0x02, r, g, b])

    # Add color_temp() if HAS_COLOR_TEMP is True
    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        kelvin = max(H6104Protocol.MIN_KELVIN, min(H6104Protocol.MAX_KELVIN, kelvin))
        warm = round(
            (H6104Protocol.MAX_KELVIN - kelvin)
            / (H6104Protocol.MAX_KELVIN - H6104Protocol.MIN_KELVIN)
            * 255
        )
        cold = 255 - warm
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
```

**3. Register in ModelRegistry** (`protocols.py`)

Add to `ModelRegistry._REGISTRY`:
```python
_REGISTRY: ClassVar[dict[str, type[GoveeProtocol]]] = {
    "ihoment_H6006": H6006Protocol,
    "ihoment_H6008": H6008Protocol,
    "ihoment_H6009": H6009Protocol,
    "ihoment_H6003": H6003Protocol,
    "ihoment_H6104": H6104Protocol,  # New model
}
```

**4. Add to MODEL_REGISTRY** (`const.py`)

```python
MODEL_REGISTRY = {
    # ... existing models ...
    "H6104": {
        "name": "Govee H6104",
        "discovery_prefix": "ihoment_H6104",
        "write_uuid": "00010203-0405-0607-0809-0a0b0c0d2b11",
        "read_uuid": "00010203-0405-0607-0809-0a0b0c0d2b10",
        "min_kelvin": 2700,  # or None if RGB-only
        "max_kelvin": 6500,  # or None if RGB-only
        "protocol_class": "H6104Protocol",
        "capabilities": {
            "color_temp": True,  # or False
            "music_sync": False,
            "scene_modes": False,
        },
    },
}
```

**5. Update manifest.json**

Add discovery prefix to Bluetooth matcher:
```json
{
  "bluetooth": [
    {"local_name": "ihoment_H6006*"},
    {"local_name": "ihoment_H6008*"},
    {"local_name": "ihoment_H6009*"},
    {"local_name": "ihoment_H6003*"},
    {"local_name": "ihoment_H6104*"}
  ]
}
```

**6. Import Protocol Class** (`api.py`)

Add import for the new protocol:
```python
from .protocols import (
    GoveeProtocol,
    H6003Protocol,
    H6006Protocol,
    H6008Protocol,
    H6009Protocol,
    H6104Protocol,  # New
)
```

**7. Write Tests** (`tests/test_protocols.py`)

Add comprehensive tests for the new protocol:
```python
class TestH6104Protocol:
    def test_power_on(self):
        result = H6104Protocol.power(True)
        assert len(result) == 20
        assert result[0] == 0x33
        assert result[1] == 0x01
        assert result[2] == 0x01

    def test_power_off(self):
        result = H6104Protocol.power(False)
        assert result[2] == 0x00

    # ... test_brightness, test_color_rgb, test_color_temp, etc.
```

**8. Update Documentation**

- Update this CLAUDE.md file with the new model in the "Supported Models" list
- Update README.md with model capabilities
- Add protocol details to CHANGELOG.md

**9. Hardware Verification**

If possible, test with actual hardware:
- Verify auto-discovery works
- Test all commands (power, brightness, RGB, color temp if applicable)
- Verify state updates via BLE notifications
- Update protocol class docstring to note "Hardware verified"

## Bluetooth Resilience

To handle noisy RF environments (e.g., 2.4GHz interference from WiFi, cordless phones, microwaves):
- **Connection timeout:** 20 seconds (api.py line 196) — allows retry mechanism more time to establish connection
- **Polling interval:** 30 seconds (coordinator.py line 42) — reduces polling frequency to be less aggressive in noisy environments
- **Connection lock:** asyncio.Lock prevents concurrent connection attempts, avoiding "Operation already in progress" BlueZ errors (api.py line 54)

These settings help stabilize Bluetooth in interference-prone home networks. If further issues persist, consider placing the BLE adapter away from USB 3 sources.

## Instant UI Responsiveness

Commands sent from Home Assistant provide **instant UI feedback** via optimistic updates (coordinator.py lines 72–82). When you adjust brightness, color, or power state:
1. Local state updates immediately → UI reflects change instantly
2. Command is sent to device asynchronously
3. Notification updates are **suppressed for 500ms** to prevent stale state from overwriting optimistic updates (api.py line 45)
4. Device processes command and sends confirmation via notification or polling (fallback after 30s)

This architecture prevents the device from echoing back old state before processing the command, which was causing the "restore to last settings" issue. All commands and notifications are logged at debug level for troubleshooting.

## Staying Current

Before working on a task, check that this documentation matches the current codebase:
- Verify test commands still work: `pytest -x -q`
- Check that module paths haven't changed
- Confirm the coordinator still uses 30s polling (see coordinator.py line 42)
- Verify connection timeout is 20s in api.py (line 196)
- Review recent commits to catch breaking changes not yet documented here

If you notice discrepancies, update this CLAUDE.md to reflect the current state.

## Summary of previous session

Built a custom HACS integration (govee_h6006) for the Govee H6006 bulb using local BLE only — no cloud.                                                                         
   
  What We Built                                                                                                                                                                                                                     
  - manifest.json — connectable: true (the critical fix over the reference integration), iot_class: local_push                                                                    
  - const.py — Domain, UUIDs, kelvin range (2700–6500K)
  - api_utils.py — 20-byte Govee packet builder (XOR checksum, power/brightness/RGB/color-temp commands)
  - api.py — Persistent GATT connection via bleak-retry-connector (20s timeout, asyncio.Lock to prevent concurrent connections), notification handler for push state updates, poll_state to query current device state on demand
  - coordinator.py — DataUpdateCoordinator with BLE push as primary, 30s polling fallback that refreshes the BLE device handle and calls poll_state
  - config_flow.py — Auto-discovery (async_step_bluetooth) + manual user flow; connectable=True throughout
  - light.py — LightEntity supporting RGB + color temp modes
  - __init__.py — Setup/unload entry points
  - translations/en.json, hacs.json — HACS distribution files

  Bugs Fixed During Hardware Testing

  1. "Invalid flow specified" — Config flow overrode async_show_form/async_create_entry/async_abort with test stubs that broke HA's flow machinery. Removed them.
  2. All states "Unknown", can't control — _async_update_data returned empty snapshot instead of connecting. Fixed by adding poll_state to the API and making the coordinator
  refresh the BLE device handle + query state on each poll.

  Test Coverage

  105 tests across all modules, all passing. Coverage: 92.74% (exceeds 90% target).