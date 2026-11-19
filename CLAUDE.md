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
├── protocols/           # Pluggable protocol layer
│   ├── base.py         # GoveeProtocol — abstract interface for all protocols
│   ├── h6006.py        # H6006Protocol — packet building for H6006
│   ├── h6008.py        # H6008Protocol — packet building for H6008
│   ├── h6009.py        # H6009Protocol — packet building for H6009
│   ├── h6003.py        # H6003Protocol — packet building for H6003
│   └── __init__.py     # Protocol exports
├── api.py              # GoveeAPI — BLE connection, writes commands via protocol, device info queries
├── coordinator.py      # GoveeCoordinator (DataUpdateCoordinator) — polls every 30s, proxies commands
├── config_flow.py      # Multi-model Bluetooth discovery + manual setup flow
├── light.py            # GoveeLight (LightEntity) — RGB + color temp modes (RGB only when model lacks color_temp capability)
├── const.py            # MODEL_REGISTRY, UUIDs (GATT + BLE DIS), domain, kelvin range
├── sensor.py           # Diagnostic sensors (connection state, RSSI, firmware version)
└── translations/       # UI strings
```

**Multi-model protocol architecture:** The integration uses a pluggable protocol system to support multiple Govee models (H6006, H6008, H6009, H6003). Each protocol class implements the `GoveeProtocol` interface with static methods for command packet building (power, brightness, RGB, color temp). Protocol selection happens automatically based on the `model_type` config entry field. All protocols build 20-byte packets with command frames (head `0x33`) and XOR checksum validation.

**Smooth transitions:** Software-based linear interpolation for brightness, RGB, and color temperature. Enabled via the `transition` parameter in `light.turn_on`. Managed by `Coordinator` tasks with 0.1s update intervals. Any instant command cancels a running transition.

**Non-blocking device info:** Firmware, hardware, and model are queried asynchronously after setup. Initial setup uses a 2-attempt fast-fail limit to avoid blocking Home Assistant startup.

**Two packet heads:** Command frames use `0x33` (built by protocol classes). Query/response frames use `0xAA` (built/parsed in `api.py`). Both are 20 bytes with XOR checksum in the last byte.

**Data flow:** `LightEntity` -> `GoveeCoordinator` -> `GoveeAPI(model_type)` -> Protocol class static methods -> BLE write. Notifications flow back via `_handle_notification` callback -> `coordinator.async_set_updated_data`.

**Adding new models:** See `docs/adding_new_models.md` for a complete guide on creating new protocol classes for additional Govee models.

**Device info:** Firmware version, hardware revision, and model number are queried from standard BLE Device Information Service (DIS) characteristics on startup. The `GoveeAPI.query_device_info()` method reads these characteristics and stores them as instance attributes. The coordinator calls this method in a background task during initialization and logs firmware version at INFO level. Device info is displayed in the Home Assistant device info panel via the `device_info` property on entity classes.

**Test stubs:** `conftest.py` patches `sys.modules` to stub all external dependencies (homeassistant, bleak, voluptuous). Tests run without any of these packages installed. The `_FlowManager` in conftest directly invokes config flow steps.

## Protocol Reference

| Command | Head | Cmd | Payload |
|---------|------|-----|---------|
| Power   | 0x33 | 0x01 | 0x01 (on) / 0x00 (off) |
| Brightness | 0x33 | 0x04 | 0-255 |
| RGB color | 0x33 | 0x05 | 0x02, R, G, B |
| Color temp | 0x33 | 0x05 | 0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold |

Color temp range: 2700K–6500K. Warm/cold bytes are complementary (sum to 255).

## Device Information

Device information is queried from standard BLE Device Information Service (DIS) characteristics:

| Characteristic | UUID | Description |
|----------------|------|-------------|
| Firmware Revision | 0x2A26 | Firmware version string |
| Hardware Revision | 0x2A27 | Hardware revision string |
| Model Number | 0x2A24 | Device model number |
| Manufacturer Name | 0x2A29 | Manufacturer name string |

The `query_device_info()` method in `api.py` reads these characteristics during initialization. If a characteristic is missing or unreadable, the value is set to "Unknown". Firmware version is logged at INFO level on startup to aid in debugging. All device info is exposed in the Home Assistant device info panel via the `device_info` property on entity classes (`light.py`, `sensor.py`).

## Bluetooth Resilience

To handle noisy RF environments (e.g., 2.4GHz interference from WiFi, cordless phones, microwaves):
- **Connection timeout:** 20 seconds per attempt, enforced with `asyncio.wait_for` in `GoveeAPI._retry_connection` (bleak-retry-connector ignores a timeout kwarg). `establish_connection` is called with `max_attempts=1`; our loop owns retries and backoff.
- **Polling interval:** 30 seconds (coordinator.py line 42) — reduces polling frequency to be less aggressive in noisy environments
- **Connection lock:** asyncio.Lock prevents concurrent connection attempts, avoiding "Operation already in progress" BlueZ errors. Held per attempt only, never during backoff sleeps.

These settings help stabilize Bluetooth in interference-prone home networks. If further issues persist, consider placing the BLE adapter away from USB 3 sources.

## Instant UI Responsiveness

Commands sent from Home Assistant provide **instant UI feedback** via optimistic updates (coordinator.py lines 72–82). When you adjust brightness, color, or power state:
1. Local state updates immediately → UI reflects change instantly
2. Command is sent to device asynchronously
3. Notification updates are **suppressed for 500ms** to prevent stale state from overwriting optimistic updates (`_suppress_update_until` in api.py). Notifications outside that window are never throttled, so all poll replies reach HA.
4. Device processes command and sends confirmation via notification or polling (fallback after 30s)

This architecture prevents the device from echoing back old state before processing the command, which was causing the "restore to last settings" issue. All commands and notifications are logged at debug level for troubleshooting.

## Staying Current

Before working on a task, check that this documentation matches the current codebase:
- Verify test commands still work: `pytest -x -q`
- Check that module paths haven't changed
- Confirm the coordinator still uses 30s polling (see coordinator.py line 42)
- Verify connection timeout is 20s (`DEFAULT_CONNECTION_TIMEOUT` in const.py)
- Review recent commits to catch breaking changes not yet documented here

If you notice discrepancies, update this CLAUDE.md to reflect the current state.

## Summary of previous sessions

Built a custom HACS integration (govee_h6006) for the Govee H6006 bulb using local BLE only — no cloud.

  What We Built
  - manifest.json — connectable: true (the critical fix over the reference integration), iot_class: local_push
  - const.py — Domain, UUIDs, kelvin range (2700–6500K)
  - protocols/base.py — GoveeProtocol abstract interface defining build_*_packet() and parse_notification() methods
  - protocols/h6006.py — H6006Protocol implementation (20-byte packets, XOR checksum, power/brightness/RGB/color-temp commands)
  - protocols/__init__.py — Protocol registry mapping device name prefixes to protocol classes, get_protocol() factory
  - api.py — Persistent GATT connection via bleak-retry-connector (20s timeout, asyncio.Lock to prevent concurrent connections), notification handler for push state updates, poll_state to query current device state on demand. Uses protocol abstraction for all packet building and parsing.
  - coordinator.py — DataUpdateCoordinator with BLE push as primary, 30s polling fallback that refreshes the BLE device handle and calls poll_state. Selects protocol via get_protocol(device_name).
  - config_flow.py — Auto-discovery (async_step_bluetooth) + manual user flow; connectable=True throughout
  - light.py — LightEntity supporting RGB + color temp modes
  - __init__.py — Setup/unload entry points
  - translations/en.json, hacs.json — HACS distribution files
  - docs/adding_new_models.md — Developer guide for adding support for new Govee models via protocol abstraction

  Bugs Fixed During Hardware Testing

  1. "Invalid flow specified" — Config flow overrode async_show_form/async_create_entry/async_abort with test stubs that broke HA's flow machinery. Removed them.
  2. All states "Unknown", can't control — _async_update_data returned empty snapshot instead of connecting. Fixed by adding poll_state to the API and making the coordinator
  refresh the BLE device handle + query state on each poll.

  Architecture Refactoring

  Refactored from hardcoded H6006 protocol to pluggable architecture for multi-model support:
  - Moved packet building from GoveePacket (api_utils.py) to H6006Protocol class
  - Moved notification parsing from GoveeAPI to H6006Protocol.parse_notification()
  - Created protocol registry for automatic protocol selection based on device name
  - Removed api_utils.py module (functionality now in protocol classes)
  - All existing functionality preserved, no user-facing changes

  Test Coverage

  170 tests across all modules, all passing. Coverage: 92% (exceeds 90% target).