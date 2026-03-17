# Govee H6009 BLE Protocol Research

## Overview

The Govee H6009 is a WiFi+Bluetooth RGBWW LED smart bulb with enhanced brightness (1200 lumens) and additional features like music sync and scene modes. This document captures research on its BLE protocol structure based on similar Govee models and identifies areas requiring hardware testing for verification.

**Status:** Research in progress - protocol details need hardware verification
**Model:** H6009 (WiFi+Bluetooth RGBWW LED Bulb - 1200 Lumens)
**Related Models:** H6001 (confirmed BLE support), H6006 (confirmed working), H6008 (800 lumen variant)

## Device Specifications

### Hardware Specs
- **Brightness:** 1200 lumens (12W, equivalent to 80W incandescent)
- **Color Type:** RGBWW (RGB + Warm White + Cool White)
- **Base:** E26
- **Color Temperature Range:** 2700K - 6500K
- **CRI:** 90 (high color accuracy)
- **Connectivity:** 2.4GHz WiFi + Bluetooth BLE

### Key Features
- **Music Sync Mode:** Responds to audio detected by phone microphone
- **Scene Modes:** 54 preset dynamic lighting scenes
- **DIY Colors:** 16 million color options
- **Group Control:** Supports up to 50 bulbs
- **Voice Control:** Compatible with Alexa & Google Assistant

## Discovery & Connection

### BLE Advertising Name

**Known:** Govee devices typically advertise with one of these prefixes:
- `ihoment_` (most common for H6xxx bulbs)
- `Govee_`
- `GBK_`
- `Minger_`

**Needs Verification:** Exact advertising name prefix for H6009
**Expected:** `ihoment_H6009_XXXX` (where XXXX is device-specific)

**Evidence:** The H6001 and H6006 bulbs use `ihoment_` prefix. The H6009 is in the same product family, suggesting it follows the same pattern.

### GATT Service UUIDs

**Known from H6006:**
- Write Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b11`
- Read Characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`

**Needs Verification:** Whether H6009 uses the same UUIDs
**Expected:** Same UUIDs (common across H6xxx bulb series)

**Evidence:** Multiple sources confirm this UUID pair is used across Govee H60xx bulb models, including H6001, H6053, H6072, and H6113.

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

Based on H6006, H6001, and similar models, the following commands are expected to work with H6009:

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

**Status:** ⚠️ Needs hardware verification - H6009 likely uses simple format like H6001/H6006

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

**Status:** ⚠️ Needs hardware verification - kelvin range confirmed 2700K-6500K

## Additional Commands (H6009-Specific Features)

### Music Mode

**Command:** `0x0C` (tentative)

The H6009 supports music sync mode where the bulb changes color and brightness in response to audio detected by the phone's microphone.

**Status:** ❓ Unknown - command format needs discovery
**Priority:** High - this is a key differentiator for H6009

### Scene Mode

**Command:** `0x05`
**Sub-command:** `0x04` (tentative)

The H6009 features 54 preset scene modes with dynamic lighting effects.

**Status:** ❓ Unknown - scene selection command needs discovery
**Priority:** High - this is a key differentiator for H6009

### DIY Mode

**Command:** `0x05`
**Sub-command:** `0x0A` (tentative)

The H6009 supports custom DIY lighting patterns with 16 million color options.

**Status:** ❓ Unknown - DIY pattern command format needs discovery
**Priority:** Medium

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

**Confirmed:** Full RGB support (16 million colors per specs)
**Range:** 0-255 per channel (R, G, B)
**CRI:** 90 (high color accuracy)

### Color Temperature Mode

**Confirmed Range:** 2700K - 6500K
**Implementation:** Dual white LEDs (warm + cool)

### White Balance

**Confirmed:** RGBWW (RGB + Warm White + Cool White)

The "WW" in RGBWW indicates dual white LEDs for better color temperature rendering.

## Protocol Variations

### Expected Protocol Family

**Family 1 (H6006, H6001):**
- Simple RGB format: `33 05 02 [R] [G] [B]`
- Color temp: `33 05 02 FF FF FF 01 [WARM] [COLD]`
- Standard UUIDs: `00010203-...`

**Expected:** H6009 likely follows Family 1 (same as H6001/H6006)

**Rationale:** All three models (H6001, H6006, H6009) are RGBWW bulbs in the H60xx series. The main differences are:
- H6001: Basic model (unknown lumens)
- H6006: 800 lumens, basic features
- H6009: 1200 lumens, music sync, 54 scene modes

The enhanced features (music, scenes) are likely implemented via additional command bytes rather than a completely different protocol.

## Differences from H6006/H6008

### Brightness Difference
- **H6006/H6008:** 800 lumens (9W)
- **H6009:** 1200 lumens (12W)
- **Impact:** May affect brightness scaling or minimum brightness values

### Feature Differences
- **Music Sync:** H6009 has music mode (H6006 does not)
- **Scene Modes:** H6009 has 54 presets (H6006 unknown)
- **DIY Colors:** H6009 explicitly advertises 16M colors
- **Group Control:** H6009 supports up to 50 bulbs

### Protocol Implications

**Likely Same:**
- Basic commands (power, brightness, RGB, color temp)
- GATT UUIDs
- Packet structure and checksum
- Advertising name pattern

**Likely Different:**
- Additional command bytes for music mode
- Scene selection commands
- Possibly more advanced state queries

## Testing Protocol

To verify H6009 protocol support, perform the following tests in order:

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
- [ ] Test color temperature commands (2700K, 4600K, 6500K)
- [ ] Verify smooth transitions
- [ ] Test maximum brightness (1200 lumens vs 800)

### 5. Advanced Feature Tests
- [ ] Test music sync mode activation
- [ ] Test scene mode selection
- [ ] Test DIY color mode
- [ ] Test group control (if multiple bulbs available)

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
- [Homebridge Govee Plugin Supported Devices](https://github.com/homebridge-plugins/homebridge-govee/wiki/Supported-Devices) - H6001 confirmed, H6009 uncertain
- [Govee H6009 User Manual](https://manuals.plus/govee/h6009-wifibluetooth-rgbww-led-bulb-manual)

### Product Information

- [Govee H6009 Official Page](https://us.govee.com/products/govee-wi-fi-bluetooth-led-bulbs-2-pack)
- [Govee H6009 Specifications](https://manuals.plus/m/12d9efe7eb14f11f5e7e318ff0bb97505b4da4ae5d93adbd830760c0df880a82)

## Known vs Unknown Summary

### ✅ Known (High Confidence)

| Item | Value | Source |
|------|-------|--------|
| Brightness | 1200 lumens | Official specs |
| Power | 12W | Official specs |
| Color Type | RGBWW | Official specs |
| Color Temp Range | 2700K - 6500K | Official specs |
| Base Type | E26 | Official specs |
| Connectivity | WiFi + BLE | Official specs |
| Music Sync | Supported | Official specs |
| Scene Modes | 54 presets | Official specs |
| DIY Colors | 16 million | Official specs |

### ⚠️ Likely (Needs Verification)

| Item | Expected Value | Rationale |
|------|---------------|-----------|
| Advertising Name | `ihoment_H6009_XXXX` | Same pattern as H6001/H6006 |
| Write UUID | `00010203-0405-0607-0809-0a0b0c0d2b11` | Standard across H60xx bulbs |
| Read UUID | `00010203-0405-0607-0809-0a0b0c0d2b10` | Standard across H60xx bulbs |
| Power Command | `0x01` | Same as H6001/H6006 |
| Brightness Command | `0x04` | Same as H6001/H6006 |
| Color Command | `0x05` | Same as H6001/H6006 |
| RGB Format | `33 05 02 [R] [G] [B]` | Same as H6001/H6006 |
| Color Temp Format | `33 05 02 FF FF FF 01 [W] [C]` | Same as H6001/H6006 |

### ❓ Unknown (Requires Hardware Testing)

| Item | Status | Priority |
|------|--------|----------|
| Exact advertising name | Unknown | High |
| Music sync command | Unknown | High |
| Scene selection command | Unknown | High |
| DIY mode command | Unknown | Medium |
| Status query format | Unknown | Medium |
| Brightness range (min/max) | Unknown | Medium |
| Group control commands | Unknown | Low |

## Next Steps

1. **Hardware Acquisition:** Obtain H6009 device for testing
2. **BLE Sniffing:** Capture actual BLE traffic using nRF Connect or Wireshark
3. **Basic Protocol Verification:** Confirm power/brightness/color commands match H6006
4. **Advanced Feature Discovery:** Reverse engineer music sync and scene mode commands
5. **Implementation:** Create H6009Protocol class based on verified commands
6. **Testing:** Build comprehensive test suite including advanced features
7. **Documentation:** Update this document with verified protocol details

## Status Summary

| Feature | Status | Confidence | Notes |
|---------|--------|------------|-------|
| Advertising Name | ⚠️ Needs Verification | High | Expected: `ihoment_H6009_XXXX` |
| GATT UUIDs | ⚠️ Needs Verification | High | Expected: Same as H6006 |
| Power Command | ⚠️ Needs Verification | High | Format likely identical to H6006 |
| Brightness Command | ⚠️ Needs Verification | High | Range may vary (1200 vs 800 lumens) |
| RGB Color Command | ⚠️ Needs Verification | High | Format likely identical to H6006 |
| Color Temp Command | ⚠️ Needs Verification | High | Range confirmed 2700K-6500K |
| Status Query | ❓ Unknown | Medium | Need to discover query method |
| Music Mode | ❓ Unknown | Low | Key H6009 feature - needs discovery |
| Scene Mode | ❓ Unknown | Low | Key H6009 feature - needs discovery |
| DIY Mode | ❓ Unknown | Low | Needs discovery |

---

**Last Updated:** 2026-03-16
**Research Status:** Initial research complete, hardware verification required
**Key Finding:** H6009 likely uses same basic protocol as H6001/H6006 with additional commands for music sync and scene modes
