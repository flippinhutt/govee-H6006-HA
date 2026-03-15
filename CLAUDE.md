# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. ALWAYS update CLAUDE.md and CHANGELOG.md when changes are made. 

## Project

HACS custom integration for the Govee H6006 light bulb. This integration uses **Bluetooth Low Energy (BLE) only** — not WiFi — for local-only control with zero cloud dependency. The H6006 device supports both BLE and WiFi, but we deliberately use BLE to avoid cloud connectivity requirements. Targets Home Assistant with `bleak` + `bleak-retry-connector` for BLE communication.

Domain: `govee_h6006`. Discovery prefix: `ihoment_*`.

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
├── api_utils.py      # GoveePacket — builds 20-byte BLE command frames (head 0x33)
├── api.py            # GoveeAPI — BLE connection, writes commands, parses notifications (head 0xAA)
├── coordinator.py    # GoveeCoordinator (DataUpdateCoordinator) — polls every 30s, proxies commands
├── config_flow.py    # Bluetooth discovery + manual user setup flow
├── light.py          # GoveeLight (LightEntity) — RGB + color temp modes
├── const.py          # UUIDs, domain, kelvin range
└── translations/     # UI strings
```

**Two packet heads:** Command frames use `0x33` (built by `GoveePacket` in `api_utils.py`). Query/response frames use `0xAA` (built/parsed in `api.py`). Both are 20 bytes with XOR checksum in the last byte.

**Data flow:** `LightEntity` -> `GoveeCoordinator` -> `GoveeAPI` -> BLE write. Notifications flow back via `_handle_notification` callback -> `coordinator.async_set_updated_data`.

**Test stubs:** `conftest.py` patches `sys.modules` to stub all external dependencies (homeassistant, bleak, voluptuous). Tests run without any of these packages installed. The `_FlowManager` in conftest directly invokes config flow steps.

## Protocol Reference

| Command | Head | Cmd | Payload |
|---------|------|-----|---------|
| Power   | 0x33 | 0x01 | 0x01 (on) / 0x00 (off) |
| Brightness | 0x33 | 0x04 | 0-255 |
| RGB color | 0x33 | 0x05 | 0x02, R, G, B |
| Color temp | 0x33 | 0x05 | 0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold |

Color temp range: 2700K–6500K. Warm/cold bytes are complementary (sum to 255).

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