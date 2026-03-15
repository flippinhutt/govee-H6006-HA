# Changelog

All notable changes to the Govee H6006 Home Assistant integration are documented here.

## [Unreleased]

### Fixed
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
