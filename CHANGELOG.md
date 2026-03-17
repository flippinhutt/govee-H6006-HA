# Changelog

All notable changes to the Govee H6006 Home Assistant integration are documented here.

## [Unreleased]

### Added
- **Multi-model support** — Added support for three additional Govee bulb models: H6008 (RGBWW, 800 lm, 9W), H6009 (RGBWW, 1200 lm, 12W with music sync and scene modes), and H6003 (RGB-only, 800 lm, 9W)
- **Pluggable protocol architecture** — New `protocols.py` module with abstract `GoveeProtocol` base class and model-specific protocol implementations (H6006Protocol, H6008Protocol, H6009Protocol, H6003Protocol)
- **Model registry system** — `MODEL_REGISTRY` in `const.py` provides centralized model metadata (discovery prefixes, GATT UUIDs, capabilities, protocol classes) for easy extensibility
- **Capability-based features** — Protocol classes declare capability flags (`HAS_COLOR_TEMP`, `HAS_MUSIC_SYNC`, `HAS_SCENE_MODES`) to enable/disable features per model
- **Multi-model auto-discovery** — Config flow now auto-detects all supported models (H6006, H6008, H6009, H6003) via Bluetooth discovery prefixes
- **Code linting with ruff** — Configured in pyproject.toml with rules for code quality, import sorting, and style consistency
- **Type checking with mypy** — Strict type checking configured for core modules (api.py, coordinator.py, protocols) to catch bugs at development time
- **pyproject.toml** — Centralized configuration for ruff and mypy with project-specific rules
- **Pre-commit hook support** — Optional local setup documented in CLAUDE.md for automatic linting and type checking before commits
- **Developer guide for adding new models** — Comprehensive documentation (docs/adding_new_models.md) with step-by-step instructions for implementing support for additional Govee models
- **Firmware version detection** — Query and display device firmware version, hardware revision, and model number via standard BLE Device Information Service (DIS) characteristics. Displayed in Home Assistant device info panel and logged at INFO level on startup for troubleshooting. Gracefully handles missing characteristics by showing 'Unknown'

### Changed
- **Pluggable protocol architecture for multi-model support** — Refactored the BLE protocol layer from hardcoded H6006-specific logic into a clean, extensible abstraction. The new architecture introduces:
  - `protocols/` directory — Organized protocol implementations in a dedicated module
  - `protocols/base.py` — Abstract `GoveeProtocol` interface defining static methods for all BLE commands (power, brightness, RGB, color temp)
  - `protocols/h6006.py`, `h6008.py`, `h6009.py`, `h6003.py` — Model-specific protocol implementations with 20-byte packet building and capability flags
  - `protocols/__init__.py` — Exports all protocol classes for clean imports
  - **Benefits:** Adding support for new Govee models now requires only creating a new protocol class — no changes to core API or coordinator code. This positions the integration for easy ecosystem growth.
  - **Migration:** Moved packet building logic from `api_utils.py` (deleted) to protocol classes. All existing functionality preserved with zero user-facing changes.
- **Config entry structure** — Config entries now include a `model` field to store detected model type (defaults to "H6006" for backward compatibility with existing installations)
- **GoveeAPI protocol selection** — API now accepts `model_type` parameter and uses appropriate protocol class for command generation
- **Bluetooth matchers in manifest.json** — Replaced single wildcard pattern with explicit discovery prefixes for each supported model (ihoment_H6006, ihoment_H6008, ihoment_H6009, ihoment_H6003)

### Fixed
- **Connection timeout discrepancy** — Harmonized connection timeout values across documentation and code. CLAUDE.md now correctly documents the 20-second timeout used in api.py, ensuring consistency between implementation and documentation
- **Optimistic updates for instant UI responsiveness** — Commands sent from Home Assistant (power, brightness, color) now update the local coordinator state immediately
- **State reversion bug** — Device no longer reverts to previous values after changing state. Fixed by suppressing notifications for 500ms after sending commands, preventing the device's echoed old state from overwriting optimistic updates
- **Color mode detection** — Improved detection of white mode vs RGB mode by checking RGB values (0xFF) instead of relying on potentially unreliable frame bytes
- **Debug logging** — Added comprehensive debug logging for all commands, notifications, and polling for troubleshooting connection issues

## [0.1.0] - 2026-03-13

### Added
- **Initial HACS integration** for the Govee H6006 light bulb using Bluetooth Low Energy (BLE) only
- **Local-only control** — Zero cloud dependency, all commands via BLE
- **Auto-discovery** — Bluetooth discovery in Home Assistant config flow with manual setup option
- **RGB color support** — Full RGB color control via BLE
- **Color temperature support** — Warm to cold adjustment (2700K–6500K)
- **Brightness control** — 0-255 brightness levels
- **Power control** — Turn light on/off
- **Polling fallback** — 30-second polling interval for state synchronization
- **BLE push notifications** — Real-time state updates via device notifications
- **Connection resilience** — 20-second connection timeout and asyncio lock to prevent concurrent connection attempts in noisy RF environments
- **Test coverage** — 36+ unit and integration tests with 80%+ coverage

### Fixed
- "Invalid flow specified" error in config flow by removing test stub overrides
- "Unknown" state for all attributes by implementing poll_state in API and refreshing BLE device handle on each poll

### Technical Details
- Built with `bleak-retry-connector` for reliable BLE communication
- 20-byte Govee packet protocol (0x33 for commands, 0xAA for responses)
- XOR checksum validation on all packets
- Async/await patterns throughout for responsive control

---

## Version History

- **v0.1.0** — Mar 13, 2026 — Initial release
