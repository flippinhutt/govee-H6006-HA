# Internal API Reference - Govee H6006 BLE

This document provides a reference for the internal classes and methods used within the Govee H6006 integration.

## GoveeAPI Class

`custom_components.govee_h6006.api.GoveeAPI`

The core class responsible for BLE communication.

### Methods

| Method | Description |
|--------|-------------|
| `query_device_info()` | Reads device firmware, hardware, and model information. |
| `update_device(ble_device)` | Updates the internal BLEDevice handle (used when discovery refreshes the device). |

### Properties

- `address`: Returns the Bluetooth MAC address of the device.
- `is_available`: Returns True if the device is connected or in a retryable state.
- `connection_state`: Returns a human-readable string of the current connection status for diagnostics.
- `connection_success_rate`: Percentage of successful connection attempts over the last 10 tries.

---

## Device Protocols

`custom_components.govee_h6006.protocols`

The integration uses model-specific protocol classes to construct BLE command frames.

### Supported Protocols

| Class | Model | Features |
|-------|-------|----------|
| `H6006Protocol` | H6006 | Power, Brightness, RGB, Color Temp |
| `H6008Protocol` | H6008 | Power, Brightness, RGB, Color Temp |
| `H6009Protocol` | H6009 | Power, Brightness, RGB, Color Temp (Scenes planned) |
| `H6003Protocol` | H6003 | Power, Brightness, RGB |

---

## GoveeCoordinator Class

`custom_components.govee_h6006.coordinator.GoveeCoordinator`

Manages state distribution and entity communication.

### Data Structure: `GoveeData`

```python
@dataclass
class GoveeData:
    state: bool | None
    brightness: int | None
    color_rgb: tuple[int, int, int] | None
    color_temp: int | None
    rssi: int | None
    connection_success_rate: float | None
    last_poll_time: datetime | None
    connection_state: str
    total_reconnections: int
```

### Key Responsibilities

- **Initialization**: Sets up the `GoveeAPI` and configures polling intervals from options.
- **State Merging**: Merges asynchronous push notifications from the API into the coordinator data.
- **Error Handling**: Wraps API communication in `UpdateFailed` exceptions for Home Assistant's native error handling.
- **Optimistic Logic**: Implements the rollback mechanism if a command fails after an optimistic UI update.
