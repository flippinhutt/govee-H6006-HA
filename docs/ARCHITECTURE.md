# Architecture Overview - Govee H6006 BLE Integration

This document describes the architectural design and data flow of the Govee H6006 BLE Home Assistant integration.

## System Architecture

The integration follows the standard Home Assistant Design Pattern for Data Update Coordinators, specifically tailored for Bluetooth Low Energy (BLE) communication.

```mermaid
graph TD
    HA[Home Assistant Core] --> Light[Light Entity]
    Light --> Coord[GoveeCoordinator]
    Coord --> API[GoveeAPI]
    API --> Bleak[Bleak / bleak-retry-connector]
    Bleak --> Device((Govee H6006 Bulb))

    Device -- Notifications --> API
    API -- Callback --> Coord
    Coord -- Update Data --> Light
```

## Key Components

### [GoveeAPI](file:///Users/ryanhutto/projects/govee/custom_components/govee_h6006/api.py)
The low-level interface for Bluetooth communication.
- **Connection Management**: Uses `bleak-retry-connector` for robust persistent connections with automatic retries and exponential backoff.
- **Packet Engineering**: Builds 20-byte command frames (Head `0x33`) and state-query frames (Head `0xAA`).
- **Notification Handling**: Parses asynchronous BLE notifications from the device to keep the local state in sync.
- **Optimistic Locking**: Prevents concurrent GATT operations on the same device.

### [GoveeCoordinator](file:///Users/ryanhutto/projects/govee/custom_components/govee_h6006/coordinator.py)
The primary data management layer.
- **Data Synchronization**: Maintains the `GoveeData` snapshot shared across entities.
- **Polling Strategy**: Implements a 30-second polling fallback to ensure state consistency even if notifications are missed.
- **Optimistic Updates**: Immediately updates the internal state when a command is sent, providing instant UI feedback.

### [GoveeLight](file:///Users/ryanhutto/projects/govee/custom_components/govee_h6006/light.py)
The Home Assistant entity representation.
- Maps standard Home Assistant services (`light.turn_on`, `light.turn_off`) to coordinator methods.
- Exposes attributes like brightness, RGB color, and color temperature.

## Data Flow

### Command Execution (Write)

1. User interacts with the Home Assistant Dashboard.
2. `GoveeLight.async_turn_on` is called.
3. `GoveeCoordinator` performs an **optimistic update**, refreshing the UI immediately.
4. `GoveeAPI` sends the BLE command.
5. `GoveeAPI` suppresses incoming notifications for 500ms to prevent the device's "old" state from overwriting the optimistic local update.

### State Updates (Read/Push)

- **Push (Primary)**: The device sends GATT notifications when its state changes (e.g., via the physical switch or the Govee app). `GoveeAPI` parses these and notifies the coordinator.
- **Poll (Fallback)**: Every 30 seconds, the coordinator requests a full state update from the device via `GoveeAPI.poll_state()`.

## Resilience and Stability

- **Adaptive Backoff**: Connection retries follow an exponential backoff schedule (1s, 2s, 4s, 8s, 16s) up to 5 attempts.
- **Cooldown Period**: If a device becomes unreachable, the integration enters a cooldown state for 60 seconds before resetting retry counters, preventing excessive CPU/Bluetooth usage.
- **Unified Locking**: Uses a single `asyncio.Lock` to ensure only one connection attempt or command write occurs at a time per device, preventing race conditions.
- **Connection Cleanup**: Automatically disconnects and clears the BLE client if post-connection steps (like starting notifications) fail, preventing resource leakage.
- **Enhanced Diagnostics**: Key connection events and failures are logged at the `INFO` level to provide immediate visibility into device health.
- **Configurable Suppression**: Dynamically adjusts the notification suppression window (default 500ms) to prevent stale device state from overwriting optimistic updates.

## Advanced Features

### Smooth Transitions (Software-based)

The integration implements smooth brightness and color transitions using software-based linear interpolation. When a transition duration is specified in Home Assistant:
1. The `Coordinator` cancels any existing transition tasks.
2. A new asynchronous task calculates intermediate states based on the `TRANSITION_UPDATE_INTERVAL` (default 0.1s).
3. The `Coordinator` sends sequential BLE commands for each step, updating its internal state to ensure the UI follows the transition smoothly.
4. If a manual command is received during a transition, the active transition is immediately cancelled to prioritize user intent.

### Non-blocking Initialization

To ensure a fast and reliable Home Assistant startup:
- **Asynchronous Discovery**: Device information (firmware, hardware, model) is queried in a background task after the integration has finished its main setup.
- **Fast-fail Logic**: The first state refresh uses a strict 2-attempt limit. This prevents the "Waiting for integrations to complete setup" warning if a device is temporarily out of range, allowing Home Assistant to proceed while the integration continues to try reconnecting in the background.
