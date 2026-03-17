# Govee H6003 BLE Protocol Research

## Overview

The Govee H6003 is a WiFi+Bluetooth RGB LED smart bulb in the H6xxx series. This document captures research on its BLE protocol structure based on similar Govee models and identifies areas requiring hardware testing for verification.

**Status:** Research in progress - protocol details need hardware verification
**Model:** H6003 (WiFi+Bluetooth RGB LED Bulb)
**Related Models:** H6006 (confirmed working), H6001, H6008, H6009

## Discovery & Connection

### BLE Advertising Name

**Known:** Govee devices typically advertise with one of these prefixes:
- `ihoment_` (most common for H6xxx bulbs)
- `Govee_`
- `GBK_`
- `Minger_`

**Needs Verification:** Exact advertising name prefix for H6003
**Expected:** `ihoment_H6003_XXXX` (where XXXX is device-specific)

**Evidence:** The H6001 and H6006 bulbs use `ihoment_` prefix. The H6003 is in the same product family, suggesting it follows the same pattern.

### GATT Service UUIDs

**Known from H6006:**
- Write Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b11`
- Read Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`

**Needs Verification:** Whether H6003 uses the same UUIDs
**Expected:** Same UUIDs (common across H6xxx bulb series)

**Evidence:** Multiple sources confirm this UUID pair is used across Govee H60xx bulb models, including H6001, H6006, H6053, H6072, and H6113.

## Protocol Structure

### Packet Format

All Govee BLE commands follow this structure:

```
[HEAD] [CMD] [PAYLOAD (17 bytes)] [CHECKSUM]
Total: 20 bytes
```

**Head Byte:**
- `0x33` - Command packets (sent to device)
- `0xAA` - Response/status packets (received from device)
- `0xA1` - Alternative response packet type

**Checksum:**
- Last byte (index 19)
- XOR of all previous 19 bytes
- Calculation: `byte[0] ^ byte[1] ^ ... ^ byte[18]`

### Command Structure

**Byte 0:** Head (`0x33` for commands)
**Byte 1:** Command type
**Bytes 2-18:** Command-specific payload (padded with `0x00`)
**Byte 19:** XOR checksum

## Command Reference

Based on H6006 and similar models, the following commands are expected to work with H6003:

### Power Control

**Command:** `0x01`

**Power On:**
```
33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Power Off:**
```
33 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Byte 2:** Power state
- `0x01` - On
- `0x00` - Off

**Expected Checksum:**
- Power On: `0x33`
- Power Off: `0x32`

**Status:** ⚠️ Needs hardware verification (likely identical to H6001/H6006)

### Brightness Control

**Command:** `0x04`

**Format:**
```
33 04 [BRIGHTNESS] 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Byte 2:** Brightness value
- Range: `0x00` - `0xFF` (0-255)
- Some models use `0x14` (20) as minimum (1%)
- `0xFE` (254) typically represents 100%

**Example (50% brightness = 127):**
```
33 04 7F 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 48
```

**Status:** ⚠️ Needs hardware verification

### RGB Color Control

**Command:** `0x05`
**Sub-command:** `0x02` (manual color mode)

**Format:**
```
33 05 02 [R] [G] [B] 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Bytes:**
- Byte 2: `0x02` (manual color operation mode)
- Byte 3: Red (0-255)
- Byte 4: Green (0-255)
- Byte 5: Blue (0-255)

**Example (Red = 255, 0, 0):**
```
33 05 02 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 CD
```

**Example (Green = 0, 255, 0):**
```
33 05 02 00 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 CD
```

**Example (Blue = 0, 0, 255):**
```
33 05 02 00 00 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 CD
```

**Status:** ⚠️ Needs hardware verification - H6003 likely uses simple format like H6001/H6006

### Color Temperature Control

**Command:** `0x05`
**Sub-command:** `0x02` (manual color mode)

**Note:** Color temperature support on H6003 is uncertain. The model designation and available research suggests H6003 may be RGB-only without dedicated white LEDs (unlike H6006/H6008/H6009 which are RGBWW).

**Format (if supported):**
```
33 05 02 FF FF FF 01 [WARM] [COLD] 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Bytes:**
- Byte 2: `0x02` (manual color operation mode)
- Bytes 3-5: `0xFF 0xFF 0xFF` (marks color temp mode)
- Byte 6: `0x01` (color temp flag)
- Byte 7: Warm component (0-255)
- Byte 8: Cold component (0-255)

**Temperature Calculation:**
```python
MIN_KELVIN = 2700
MAX_KELVIN = 6500
kelvin = max(MIN_KELVIN, min(MAX_KELVIN, kelvin))
warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
cold = 255 - warm
```

**Example (4600K = warm:127, cold:128):**
```
33 05 02 FF FF FF 01 7F 80 00 00 00 00 00 00 00 00 00 00 19
```

**Warm/Cold Relationship:**
- `warm + cold = 255` (complementary)
- Higher warm value = warmer/yellower light (2700K)
- Higher cold value = cooler/bluer light (6500K)

**Status:** ❓ Unknown if H6003 supports color temperature - may be RGB-only

## Additional Commands

### Music Mode

**Command:** `0x0C` (tentative)

Some Govee models support music sync mode.

**Status:** ❓ Unknown if H6003 supports this feature

### Scene Mode

**Command:** `0x05`
**Sub-command:** `0x04` (tentative)

Some Govee models support preset scene modes.

**Status:** ❓ Unknown if H6003 supports this feature

### DIY Mode

**Command:** `0x05`
**Sub-command:** `0x0A` (tentative)

Some Govee models support custom DIY lighting patterns.

**Status:** ❓ Unknown if H6003 supports this feature

## Response/Status Packets

### Status Query

Some Govee models support querying current device state.

**Query Command (Head 0xAA):**
```
AA [CMD] 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Status Response:**

Devices send status updates via notifications on the Read characteristic with head byte `0xAA`.

**Expected Response Format:**
```
AA [CMD] [STATE DATA...] [XOR]
```

**Status:** ⚠️ Needs hardware verification - determine query command and response format

## Color Capabilities

### RGB Mode

**Expected:** Full RGB support (16 million colors)
**Range:** 0-255 per channel (R, G, B)

### Color Temperature Mode

**Status:** ❓ Unknown if H6003 supports color temperature control

**Note:** Unlike H6006/H6008/H6009 which are marketed as RGBWW (RGB + Warm White + Cool White), H6003 specifications are unclear about dedicated white LED support. Hardware testing is required to confirm whether:
1. H6003 has no color temperature support (RGB-only)
2. H6003 simulates color temperature using RGB mixing
3. H6003 has dedicated white LEDs with full color temperature support

### White Balance

**Expected:** RGB or possibly RGBWW
**Needs Verification:** Whether H6003 includes dedicated white LEDs

## Protocol Variations

### Known Govee Protocol Families

Based on reverse engineering of other Govee models:

**Family 1 (H6006, H6001):**
- Simple RGB format: `33 05 02 [R] [G] [B]`
- Color temp: `33 05 02 FF FF FF 01 [WARM] [COLD]`
- Standard UUIDs: `00010203-...`

**Family 2 (H6127, H6199):**
- Extended RGB format: `33 05 0B [R] [G] [B] ... FF 7F`
- LED segment control
- May use different UUIDs

**Family 3 (H5xxx sensors):**
- Different protocol entirely
- Broadcast-based
- Different UUID: `494e5445-4c4c-495f-524f-434b535f4857`

**Expected:** H6003 likely follows Family 1 (same as H6001/H6006)

## Testing Protocol

To verify H6003 protocol support, perform the following tests in order:

### 1. Discovery Test
- [ ] Scan for BLE devices
- [ ] Identify advertising name pattern
- [ ] Record exact device name format
- [ ] Compare with H6006 advertising name

### 2. Connection Test
- [ ] Connect to device
- [ ] Enumerate GATT services
- [ ] Verify Write/Read characteristic UUIDs
- [ ] Record any additional characteristics

### 3. Basic Command Test
- [ ] Send power on command (`33 01 01...`)
- [ ] Verify device responds
- [ ] Send power off command (`33 01 00...`)
- [ ] Monitor for notifications on Read characteristic

### 4. Control Command Tests
- [ ] Test brightness command (0%, 50%, 100%)
- [ ] Test RGB color commands (Red, Green, Blue, White)
- [ ] Test color temperature commands (if supported)
- [ ] Verify smooth transitions

### 5. Feature Discovery
- [ ] Test for music sync mode support
- [ ] Test for scene mode support
- [ ] Test for DIY mode support
- [ ] Document any H6003-specific features

### 6. Status Query Test
- [ ] Attempt status query with various command bytes
- [ ] Parse notification responses
- [ ] Document status packet format
- [ ] Compare with H6006 responses

### 7. Edge Case Tests
- [ ] Test invalid checksums (should be rejected)
- [ ] Test out-of-range values (should be clamped)
- [ ] Test rapid command succession
- [ ] Test connection recovery after power cycle

## Implementation Notes

### Checksum Calculation

```python
def calculate_checksum(packet: list[int]) -> int:
    """Calculate XOR checksum for 20-byte Govee packet."""
    checksum = 0
    for i in range(19):  # First 19 bytes
        checksum ^= packet[i]
    return checksum & 0xFF
```

### Packet Builder

```python
def build_packet(cmd: int, payload: list[int]) -> bytes:
    """Build a 20-byte command packet."""
    frame = [0x33, cmd & 0xFF] + payload
    # Pad to 19 bytes
    frame += [0] * (19 - len(frame))
    # Add checksum
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)
```

### Example Implementation

```python
class H6003Packet:
    """Packet builder for Govee H6003 BLE commands (Head 0x33)."""

    @staticmethod
    def power(on: bool) -> bytes:
        """Build a power command packet."""
        payload = [0x01 if on else 0x00]
        return build_packet(0x01, payload)

    @staticmethod
    def brightness(value: int) -> bytes:
        """Build a brightness command packet."""
        value = max(0, min(255, value))
        return build_packet(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """Build an RGB color command packet."""
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return build_packet(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        """Build a color temperature command packet.

        Note: H6003 may not support color temperature.
        This method is provided for testing purposes.
        """
        MIN_KELVIN = 2700
        MAX_KELVIN = 6500
        kelvin = max(MIN_KELVIN, min(MAX_KELVIN, kelvin))
        warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
        cold = 255 - warm
        return build_packet(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
```

## References

### Research Sources

This protocol documentation is based on reverse engineering work from:

- Govee H6006 implementation (this repository)
- [Govee-Reverse-Engineering](https://github.com/egold555/Govee-Reverse-Engineering) - Multi-model protocol documentation
- [Govee H6001 Documentation](https://github.com/egold555/Govee-Reverse-Engineering/blob/master/Products/H6001.md)
- [govee_btled](https://github.com/chvolkmann/govee_btled) - Python BLE wrapper
- [Home Assistant Govee BLE Integration](https://www.home-assistant.io/integrations/govee_ble/)
- [Bluetooth-Devices/govee-ble](https://github.com/Bluetooth-Devices/govee-ble) - Official HA BLE library

### Community Resources

- [Home Assistant Community - Govee Bluetooth Lights](https://community.home-assistant.io/t/govee-bluetooth-lights/262736)
- [Homebridge Govee Plugin Supported Devices](https://github.com/homebridge-plugins/homebridge-govee/wiki/Supported-Devices)
- [XDA: Reverse-engineered Govee Smart Lights](https://www.xda-developers.com/reverse-engineered-govee-smart-lights-smart-home/)

## Known vs Unknown Summary

### ⚠️ Likely (Needs Verification)

| Item | Expected Value | Rationale |
|------|---------------|-----------|
| Advertising Name | `ihoment_H6003_XXXX` | Same pattern as H6001/H6006 |
| Write UUID | `00010203-0405-0607-0809-0a0b0c0d2b11` | Standard across H60xx bulbs |
| Read UUID | `00010203-0405-0607-0809-0a0b0c0d2b10` | Standard across H60xx bulbs |
| Power Command | `0x01` | Same as H6001/H6006 |
| Brightness Command | `0x04` | Same as H6001/H6006 |
| Color Command | `0x05` | Same as H6001/H6006 |
| RGB Format | `33 05 02 [R] [G] [B]` | Same as H6001/H6006 |

### ❓ Unknown (Requires Hardware Testing)

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| Exact advertising name | Unknown | High | Critical for discovery |
| Color temperature support | Unknown | High | May be RGB-only |
| LED type (RGB vs RGBWW) | Unknown | High | Determines feature set |
| Brightness range (min/max) | Unknown | Medium | May differ from H6006 |
| Status query format | Unknown | Medium | Required for state polling |
| Music sync support | Unknown | Low | Unknown if available |
| Scene mode support | Unknown | Low | Unknown if available |

## Next Steps

1. **Hardware Acquisition:** Obtain H6003 device for testing
2. **BLE Sniffing:** Capture actual BLE traffic using nRF Connect or Wireshark
3. **Protocol Verification:** Confirm all command formats against real device
4. **Feature Discovery:** Determine which features are supported (color temp, music mode, scenes)
5. **Implementation:** Create H6003Protocol class based on verified commands
6. **Testing:** Build comprehensive test suite
7. **Documentation:** Update this document with verified protocol details

## Status Summary

| Feature | Status | Confidence | Notes |
|---------|--------|------------|-------|
| Advertising Name | ⚠️ Needs Verification | High | Expected: `ihoment_H6003_XXXX` |
| GATT UUIDs | ⚠️ Needs Verification | High | Expected: Same as H6006 |
| Power Command | ⚠️ Needs Verification | High | Format likely identical to H6006 |
| Brightness Command | ⚠️ Needs Verification | High | Format likely identical to H6006 |
| RGB Color Command | ⚠️ Needs Verification | High | Format likely identical to H6006 |
| Color Temp Command | ❓ Unknown | Low | May not be supported (RGB-only?) |
| Status Query | ❓ Unknown | Medium | Need to discover query method |
| Music Mode | ❓ Unknown | Low | Feature support uncertain |
| Scene Mode | ❓ Unknown | Low | Feature support uncertain |

## Key Unknowns Requiring Hardware Testing

**Critical Questions:**
1. **Is H6003 RGB-only or RGBWW?** This fundamentally affects the feature set and implementation.
2. **What is the exact BLE advertising name?** Required for auto-discovery.
3. **Does H6003 support color temperature control?** If RGB-only, this feature should be disabled.
4. **What is the brightness range?** Need to verify min/max values for proper scaling.

**Recommended Testing Approach:**
1. Start with basic commands known to work across all H6xxx models (power, brightness, RGB)
2. Test color temperature support to determine if H6003 has white LEDs
3. Explore advanced features (music mode, scenes) if supported
4. Document any H6003-specific behavior or limitations

---

**Last Updated:** 2026-03-16
**Research Status:** Initial research complete, hardware verification required
**Key Finding:** H6003 likely uses same basic BLE protocol as H6001/H6006, but color temperature support is uncertain and requires hardware testing to confirm LED type (RGB vs RGBWW)
