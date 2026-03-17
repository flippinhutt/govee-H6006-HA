# Govee H6008 BLE Protocol Research

## Overview

The Govee H6008 is a WiFi+Bluetooth RGBWW LED smart bulb. This document captures research on its BLE protocol structure based on similar Govee models and identifies areas requiring hardware testing for verification.

**Status:** Research in progress - protocol details need hardware verification
**Model:** H6008 (WiFi+Bluetooth RGBWW LED Bulb)
**Related Models:** H6006 (confirmed working), H6001, H6009, H6003

## Discovery & Connection

### BLE Advertising Name

**Known:** Govee devices typically advertise with one of these prefixes:
- `ihoment_` (most common for H6xxx bulbs)
- `Govee_`
- `GBK_`
- `Minger_`

**Needs Verification:** Exact advertising name prefix for H6008
**Expected:** `ihoment_H6008_XXXX` (where XXXX is device-specific)

### GATT Service UUIDs

**Known from H6006:**
- Write Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b11`
- Read Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`

**Needs Verification:** Whether H6008 uses the same UUIDs
**Expected:** Same UUIDs (common across H6xxx bulb series)

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

Based on H6006 and similar models, the following commands are expected to work with H6008:

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

**Status:** ⚠️ Needs hardware verification

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

**Alternative RGB Format (some models):**

Some Govee models use bytes 8-9 for LED segment selection:
```
33 05 0B [R] [G] [B] 00 00 FF 7F 00 00 00 00 00 00 00 00 00 [XOR]
```
- Bytes 8-9: `0xFF 0x7F` (all LED segments)

**Status:** ⚠️ Needs hardware verification - determine which format H6008 uses

### Color Temperature Control

**Command:** `0x05`
**Sub-command:** `0x02` (manual color mode)

**Format:**
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

**Status:** ⚠️ Needs hardware verification - confirm kelvin range for H6008

## Additional Commands

### Music Mode

**Command:** `0x0C`

Some Govee models support music sync mode. Format varies by model.

**Status:** ❓ Unknown if H6008 supports this feature

### Scene Mode

**Command:** `0x05`
**Sub-command:** `0x04`

Some Govee models support preset scene modes.

**Status:** ❓ Unknown if H6008 supports this feature

### DIY Mode

**Command:** `0x05`
**Sub-command:** `0x0A`

Some Govee models support custom DIY lighting patterns.

**Status:** ❓ Unknown if H6008 supports this feature

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

**Expected Range:** 2700K - 6500K
**Needs Verification:** Actual supported range for H6008

**Note:** Some Govee bulbs have different ranges:
- Standard range: 2700K - 6500K
- Extended warm: 2200K - 6500K
- Extended cool: 2700K - 9000K

### White Balance

**Expected:** RGBWW (RGB + Warm White + Cool White)

The "WW" in RGBWW indicates dual white LEDs for better color temperature rendering.

**Status:** ⚠️ Needs hardware verification

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

**Expected:** H6008 likely follows Family 1 (same as H6006)

## Testing Protocol

To verify H6008 protocol support, perform the following tests in order:

### 1. Discovery Test
- [ ] Scan for BLE devices
- [ ] Identify advertising name pattern
- [ ] Record exact device name format

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
- [ ] Test color temperature commands (2700K, 4600K, 6500K)
- [ ] Verify smooth transitions

### 5. Status Query Test
- [ ] Attempt status query with various command bytes
- [ ] Parse notification responses
- [ ] Document status packet format

### 6. Edge Case Tests
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

## References

### Research Sources

This protocol documentation is based on reverse engineering work from:

- Govee H6006 implementation (this repository)
- [Govee-Reverse-Engineering](https://github.com/egold555/Govee-Reverse-Engineering) - Multi-model protocol documentation
- [Govee H6127 Reverse Engineering](https://github.com/BeauJBurroughs/Govee-H6127-Reverse-Engineering)
- [Govee H6199 Reverse Engineering](https://github.com/ihoment-hch/Govee-H6199-Reverse-Engineering)
- [govee_btled](https://github.com/chvolkmann/govee_btled) - Python BLE wrapper
- [Home Assistant Govee BLE Integration](https://www.home-assistant.io/integrations/govee_ble/)

### Community Resources

- [Govee BLE Lights HA Integration](https://github.com/Beshelmek/govee_ble_lights) - Issue #30, #54 discuss H6008
- [XDA: Reverse-engineered Govee Smart Lights](https://www.xda-developers.com/reverse-engineered-govee-smart-lights-smart-home/)

## Next Steps

1. **Hardware Acquisition:** Obtain H6008 device for testing
2. **BLE Sniffing:** Capture actual BLE traffic using nRF Connect or Wireshark
3. **Protocol Verification:** Confirm all command formats against real device
4. **Implementation:** Create H6008Protocol class based on verified commands
5. **Testing:** Build comprehensive test suite
6. **Documentation:** Update this document with verified protocol details

## Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Advertising Name | ⚠️ Needs Verification | Expected: `ihoment_H6008_XXXX` |
| GATT UUIDs | ⚠️ Needs Verification | Expected: Same as H6006 |
| Power Command | ⚠️ Needs Verification | Format likely identical to H6006 |
| Brightness Command | ⚠️ Needs Verification | Range may vary |
| RGB Color Command | ⚠️ Needs Verification | Need to determine format variant |
| Color Temp Command | ⚠️ Needs Verification | Need to confirm kelvin range |
| Status Query | ❓ Unknown | Need to discover query method |
| Music Mode | ❓ Unknown | Feature support uncertain |
| Scene Mode | ❓ Unknown | Feature support uncertain |

---

**Last Updated:** 2026-03-16
**Research Status:** Initial research complete, hardware verification required
