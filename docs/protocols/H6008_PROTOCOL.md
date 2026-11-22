# Govee H6008 BLE Protocol Research

## Overview

The Govee H6008 is a WiFi+Bluetooth RGBWW LED smart bulb. This document captures research on its BLE protocol structure based on similar Govee models and identifies areas requiring hardware testing for verification.

**Status:** Power, brightness, RGB, color temperature and state replies verified on hardware (hardware version 1.02.01, 2026-11-22). Music, scene and DIY modes are still unverified.
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

**Byte 2:** Brightness as a percentage, 1-100 (`0x01`-`0x64`).
The bulb also stores values above 100 and reports them back unchanged, but the Govee app
sends 0-100, so the integration converts HA's 0-255 to 1-100.

**Example (20%):**
```
33 04 14 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 23
```

**Status:** ✅ Verified on hardware

### RGB Color Control

**Command:** `0x05`
**Sub-command:** `0x0D`

**Format:**
```
33 05 0D [R] [G] [B] 00 00 00 00 00 00 00 00 00 00 00 00 00 [XOR]
```

**Example (Green = 0, 255, 0):**
```
33 05 0D 00 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 C4
```

The H6006's `33 05 02 [R] [G] [B]` is rejected: the bulb answers `33 05 01 …` (status 1)
and the color doesn't change.

**Status:** ✅ Verified on hardware

### Color Temperature Control

**Command:** `0x05`
**Sub-command:** `0x0D`

**Format:**
```
33 05 0D [TR] [TG] [TB] [K_HI] [K_LO] [TR] [TG] [TB] 00 00 00 00 00 00 00 00 [XOR]
```

**Bytes:**
- Bytes 3-5 and 8-10: tint, the RGB of a black body at that temperature, as the Govee app sends it
- Bytes 6-7: Kelvin, big-endian (2700 = `0A 8C`, 6500 = `19 64`)

The integration rounds Kelvin to 100 K steps and clamps it to 2700-6500 K. The tint comes
from Tanner Helland's black-body fit.

**Example (2700 K):**
```
33 05 0D FF A7 57 0A 8C FF A7 57 00 00 00 00 00 00 00 00 BD
```

The H6006's `33 05 02 FF FF FF 01 [WARM] [COLD]` is rejected with status 1.

**Status:** ✅ Verified on hardware (2700 K, 3500 K, 4000 K, 6500 K)

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

**Verified replies on the H6008:**

| Query | Reply | Meaning |
|-------|-------|---------|
| `AA 01` | `AA 01 01` | Power on (`00` = off) |
| `AA 04` | `AA 04 64` | Brightness in percent (100) |
| `AA 05` | `AA 05 0D 00 FF 00 00 00` | RGB mode, green (Kelvin bytes zero) |
| `AA 05` | `AA 05 0D FF C9 87 0D AC` | Color temp mode, 3500 K, tint `FF C9 87` |

Commands are acknowledged with `33 [CMD] [STATUS]`: `00` = accepted, `01` = rejected.

The bulb has no Device Information Service: model, firmware and hardware revision
characteristics are not present.

**Status:** ✅ Verified on hardware

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
| Advertising Name | ✅ Verified | `ihoment_H6008_XXXX`, manufacturer data unencrypted (header `0x02`) |
| GATT UUIDs | ✅ Verified | Same as H6006 |
| Power Command | ✅ Verified | Same as H6006 |
| Brightness Command | ✅ Verified | Percent, 1-100 |
| RGB Color Command | ✅ Verified | `33 05 0D R G B` |
| Color Temp Command | ✅ Verified | `33 05 0D tint K_hi K_lo tint`, 2700-6500 K |
| Status Query | ✅ Verified | `AA 01`, `AA 04`, `AA 05` |
| Device Info (DIS) | ❌ Not present | |
| Music Mode | ❓ Unknown | Feature support uncertain |
| Scene Mode | ❓ Unknown | Feature support uncertain |

---

**Last Updated:** 2026-11-22
**Research Status:** Core commands verified on hardware version 1.02.01. Newer H6008 firmware may encrypt BLE traffic (encryption bit `0x40` in the advertisement header); that is not supported.
