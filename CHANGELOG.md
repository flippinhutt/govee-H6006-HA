# Changelog

All notable changes to the Govee H6006 Home Assistant integration are documented here.

## [Unreleased]

### Added
- **Code linting with ruff** — Configured in pyproject.toml with rules for code quality, import sorting, and style consistency
- **Type checking with mypy** — Strict type checking configured for core modules (api.py, coordinator.py, protocols) to catch bugs at development time
- **pyproject.toml** — Centralized configuration for ruff and mypy with project-specific rules
- **Pre-commit hook support** — Optional local setup documented in CLAUDE.md for automatic linting and type checking before commits
- **Developer guide for adding new models** — Comprehensive documentation (docs/adding_new_models.md) with step-by-step instructions for implementing support for additional Govee models

### Changed
- **Pluggable protocol architecture for multi-model support** — Refactored the BLE protocol layer from hardcoded H6006-specific logic into a clean, extensible abstraction. The new architecture introduces:
  - `protocols/base.py` — Abstract `GoveeProtocol` interface defining methods for all BLE commands (power, brightness, RGB, color temp) and notification parsing
  - `protocols/h6006.py` — Concrete `H6006Protocol` implementation with 20-byte packet building and XOR checksum validation
  - `protocols/__init__.py` — Protocol registry with automatic device detection via name prefix matching (e.g., `ihoment_*` → `H6006Protocol`)
  - **Benefits:** Adding support for new Govee models now requires only creating a new protocol class and registering it — no changes to core API or coordinator code. This positions the integration for easy ecosystem growth.
  - **Migration:** Moved packet building logic from `api_utils.py` (deleted) to protocol classes. Moved notification parsing from `GoveeAPI` to protocol implementations. All existing functionality preserved with zero user-facing changes.
  - **Testing:** All 170 tests pass with 92% coverage. Protocol abstraction verified to match previous behavior exactly.

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
