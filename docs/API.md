# Internal API Reference - Govee H6006 BLE

This document provides a reference for the internal classes and methods used within the Govee H6006 integration.

## GoveeAPI Class

`custom_components.govee_h6006.api.GoveeAPI`

The core class responsible for BLE communication.

### Methods

| Method | Description |
|--------|-------------|
| `__init__(ble_device, update_callback, ...)` | Initializes the API client with a BLE device handle and update callback. |
| `async poll_state()` | Triggers a full state refresh from the device. |
| `async set_power(on)` | Sends a power command (True=On, False=Off). |
| `async set_brightness(value)` | Sends a brightness command (0-255). |
| `async set_color_rgb(r, g, b)` | Sends an RGB color command. |
| `async set_color_temp(kelvin)` | Sends a color temperature command (2700-6500K). |
| `update_device(ble_device)` | Updates the internal BLEDevice handle (used when discovery refreshes the device). |

### Properties

- `is_available`: Returns True if the device is connected or in a retryable state.
- `connection_state`: Returns a human-readable string of the current connection status.
- `connection_success_rate`: Percentage of successful connection attempts over the last 10 tries.

---

## GoveePacket Class

`custom_components.govee_h6006.api_utils.GoveePacket`

A static utility class for constructing BLE GATT packets.

### Static Methods

| Method | Command Head | Payload Description |
|--------|--------------|---------------------|
| `power(on)` | `0x33` | `0x01` + `0x01/0x00` |
| `brightness(value)` | `0x33` | `0x04` + `value` |
| `color_rgb(r, g, b)` | `0x33` | `0x05` + `0x02, r, g, b` |
| `color_temp(kelvin)`| `0x33` | `0x05` + `0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold` |

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
