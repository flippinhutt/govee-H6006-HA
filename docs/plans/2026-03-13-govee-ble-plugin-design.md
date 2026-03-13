# Govee H6006 BLE HACS Integration — Design

**Date:** 2026-03-13
**Status:** Approved

---

## Problem

Existing HA Govee integrations are cloud-only or fail to connect to the H6006. The `timniklas/hass-govee_light_ble` integration declares `connectable: false` in its manifest and coordinator, preventing a proper GATT connection. The result: the H6006 (`ihoment_H6006`) is discovered but cannot be controlled.

## Goal

A clean, local-only HACS integration for the Govee H6006 bulb that reliably connects via Bluetooth and exposes full light control to Home Assistant.

---

## Architecture

Standard HA custom component:

```
custom_components/govee_h6006/
├── manifest.json      # HACS metadata, connectable: true
├── const.py           # UUIDs, discovery name, domain
├── api.py             # BLE connection + packet protocol
├── coordinator.py     # DataUpdateCoordinator, state management
├── config_flow.py     # Discovery + manual setup UI
└── light.py           # LightEntity — exposes to HA
```

**BLE stack:** `bleak` + `bleak-retry-connector`
**Discovery:** passive scan for `ihoment_*`, active GATT on confirm
**manifest.json:** `connectable: true` so HA maintains a connectable device handle

---

## Features & Protocol

All commands use 20-byte BLE packets to the Govee write characteristic:

- **Service UUID:** `00010203-0405-0607-0809-0a0b0c0d1910`
- **Write UUID:** `00010203-0405-0607-0809-0a0b0c0d2b11`
- **Read UUID:** `00010203-0405-0607-0809-0a0b0c0d2b10`

Packet format: `[head][cmd][payload...padded to 19 bytes][XOR checksum]`

| Feature | Bytes | Notes |
|---|---|---|
| Power on | `0x33 0x01 0x01` | |
| Power off | `0x33 0x01 0x00` | |
| Brightness | `0x33 0x04 [0–255]` | |
| RGB color | `0x33 0x05 0x02 [R] [G] [B]` | color mode |
| Color temp | `0x33 0x05 0x02 0xFF 0xFF 0xFF 0x01 [warm] [cold]` | white mode |

HA light entity exposes: `on/off`, `brightness`, `rgb_color`, `color_temp` (Kelvin).
Setting color temp sends white mode. Setting RGB sends color mode. Scenes: out of scope.

---

## Data Flow

**Setup:**
1. HA sees `ihoment_*` advertisement → triggers `async_step_bluetooth`
2. User confirms device in UI
3. `ConfigEntry` created with address + name

**Runtime (every 15s + on command):**
1. Coordinator requests state/brightness/color — packets buffered
2. Single BLE session: connect → write all buffered packets
3. Device responds → coordinator pushes update to `LightEntity`

**User command:**
1. `LightEntity` calls `coordinator.set_*()`
2. Coordinator buffers packet(s), calls `sendPacketBuffer()`
3. Connects (or reuses connection), writes packets
4. Response updates state optimistically

**Connection strategy:** keep connection alive between calls. `bleak-retry-connector` handles reconnection on drop.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Connection failure | `bleak-retry-connector` retries; on exhaustion mark entity `unavailable` |
| Bad checksum on receive | Log warning, discard packet |
| Device not found at startup | `ConfigEntryNotReady` — HA retries after delay |
| Command while disconnected | Buffer packet, connect in `sendPacketBuffer` |

No cloud fallback. No retry loops. Log and let HA handle recovery.

---

## Testing

**Framework:** `pytest` + `pytest-homeassistant-custom-component`

- **Unit:** packet generation (correct bytes, XOR checksum), packet parsing (power/brightness/color responses)
- **Integration:** mock `BleakClient` — verify correct packets sent for each HA service call (on, off, brightness, RGB, color temp)
- **Config flow:** mock `async_discovered_service_info` returning `ihoment_H6006` device, verify flow completes

No E2E tests against real hardware.

---

## Out of Scope

- Cloud fallback
- Multi-device / other Govee models
- Scene control
- Segmented LED support
