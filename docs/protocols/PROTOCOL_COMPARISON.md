# Govee BLE Protocol Comparison Matrix

This document compares the BLE protocols across supported Govee bulb models to identify code reuse opportunities and recommend implementation architecture.

**Last Updated:** 2026-03-16
**Status:** Based on protocol research documents - requires hardware verification

---

## Executive Summary

All four models (H6006, H6008, H6009, H6003) appear to use **the same core BLE protocol** with minor variations in feature support. The key differences are:

1. **H6003** may be RGB-only (no color temperature support)
2. **H6009** has additional features (music sync, 54 scene modes)
3. **H6008** is functionally identical to H6006 with different brightness specs

**Recommended Architecture:** **Composition with shared protocol base class**

---

## Protocol Comparison Table

| Feature | H6006 | H6008 | H6009 | H6003 |
|---------|-------|-------|-------|-------|
| **Connection** |
| Advertising Prefix | `ihoment_` ✅ | `ihoment_` ⚠️ | `ihoment_` ⚠️ | `ihoment_` ⚠️ |
| Device Name Format | `ihoment_H6006_XXXX` ✅ | `ihoment_H6008_XXXX` ⚠️ | `ihoment_H6009_XXXX` ⚠️ | `ihoment_H6003_XXXX` ⚠️ |
| Write UUID | `00010203-0405-0607-0809-0a0b0c0d2b11` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| Read UUID | `00010203-0405-0607-0809-0a0b0c0d2b10` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| **Hardware** |
| LED Type | RGBWW | RGBWW | RGBWW | RGB ❓ |
| Brightness | 800 lm | 800 lm | 1200 lm | Unknown |
| Power | 9W | 9W | 12W | Unknown |
| Color Temp Range | 2700K-6500K | 2700K-6500K ⚠️ | 2700K-6500K ⚠️ | N/A ❓ |
| **Basic Commands** |
| Power (0x01) | `33 01 [00\|01]` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| Brightness (0x04) | `33 04 [0-255]` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| RGB Color (0x05) | `33 05 02 [R] [G] [B]` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| Color Temp (0x05) | `33 05 02 FF FF FF 01 [W] [C]` ✅ | Same ⚠️ | Same ⚠️ | N/A ❓ |
| **Advanced Features** |
| Music Sync | ❌ | ❌ | ✅ ❓ | ❓ |
| Scene Modes | ❌ | ❌ | ✅ (54 scenes) ❓ | ❓ |
| DIY Mode | ❌ | ❌ | ✅ ❓ | ❓ |
| **State Query** |
| Query Format | `AA [CMD]` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |
| Response Format | `AA [CMD] [DATA]` ✅ | Same ⚠️ | Same ⚠️ | Same ⚠️ |

**Legend:**
- ✅ Confirmed (hardware verified)
- ⚠️ Expected (based on research, needs hardware verification)
- ❓ Unknown (requires hardware testing)
- ❌ Not supported

---

## Command Byte Reference

### Shared Commands (All Models)

These commands are expected to work identically across all four models:

| Command | Byte | Format | Notes |
|---------|------|--------|-------|
| **Power** | `0x01` | `33 01 [00\|01] 00...` | On=0x01, Off=0x00 |
| **Brightness** | `0x04` | `33 04 [0-255] 00...` | Full range 0-255 |
| **RGB Color** | `0x05` | `33 05 02 [R] [G] [B] 00...` | Sub-cmd 0x02 for manual color |

### Model-Specific Commands

| Command | H6006 | H6008 | H6009 | H6003 | Notes |
|---------|-------|-------|-------|-------|-------|
| **Color Temp** | ✅ | ✅ ⚠️ | ✅ ⚠️ | ❓ | H6003 may not have white LEDs |
| **Music Mode** | ❌ | ❌ | ✅ ❓ | ❓ | H6009 feature - cmd unknown |
| **Scene Select** | ❌ | ❌ | ✅ ❓ | ❓ | H6009 has 54 scenes - cmd unknown |
| **DIY Pattern** | ❌ | ❌ | ✅ ❓ | ❓ | H6009 feature - cmd unknown |

### Packet Structure (Universal)

All models use the same 20-byte packet structure:

```
[HEAD] [CMD] [PAYLOAD (17 bytes)] [CHECKSUM]
Total: 20 bytes
```

- **Head:** `0x33` (command) or `0xAA` (response/query)
- **Checksum:** XOR of first 19 bytes
- **Padding:** Unused payload bytes filled with `0x00`

---

## Code Sharing Analysis

### 100% Shared Code

These components can be **completely shared** across all models:

1. **Packet builder** (`_build_frame` in `api_utils.py`)
   - XOR checksum calculation
   - 20-byte frame construction
   - Padding logic

2. **Power command** (`GoveePacket.power`)
   - Identical format: `33 01 [00|01]`
   - No model-specific variations

3. **Brightness command** (`GoveePacket.brightness`)
   - Identical format: `33 04 [0-255]`
   - No model-specific variations

4. **RGB color command** (`GoveePacket.color_rgb`)
   - Identical format: `33 05 02 [R] [G] [B]`
   - No model-specific variations

5. **GATT UUIDs** (`const.py`)
   - Write: `00010203-0405-0607-0809-0a0b0c0d2b11`
   - Read: `00010203-0405-0607-0809-0a0b0c0d2b10`
   - Same across all H60xx models

6. **Connection management** (`GoveeAPI`)
   - `establish_connection` from `bleak-retry-connector`
   - Notification handling
   - Reconnection logic with exponential backoff
   - Optimistic updates with 500ms suppression window

7. **Coordinator pattern** (`GoveeCoordinator`)
   - 30-second polling interval
   - BLE push as primary, polling as fallback
   - Device handle refresh logic

### Conditional Code

These components need **conditional logic** based on model capabilities:

1. **Color temperature command** (`GoveePacket.color_temp`)
   - **Shared by:** H6006, H6008, H6009
   - **Excluded from:** H6003 (if RGB-only)
   - **Format:** `33 05 02 FF FF FF 01 [WARM] [COLD]`
   - **Implementation:** Check model capability flag

2. **Kelvin range constants**
   - **Shared by:** H6006, H6008, H6009
   - **Range:** 2700K-6500K
   - **Implementation:** Model-specific constants

3. **Light entity features** (`LightEntity.supported_features`)
   - **H6006/H6008/H6009:** `SUPPORT_COLOR | SUPPORT_COLOR_TEMP | SUPPORT_BRIGHTNESS`
   - **H6003:** `SUPPORT_COLOR | SUPPORT_BRIGHTNESS` (no color temp)

### Model-Specific Code

These components are **unique to specific models**:

1. **Music sync mode** (H6009 only)
   - Command format: Unknown (requires hardware testing)
   - Priority: High - key H6009 differentiator

2. **Scene modes** (H6009 only)
   - 54 preset scenes
   - Command format: Unknown (requires hardware testing)
   - Priority: High - key H6009 differentiator

3. **DIY patterns** (H6009 only)
   - Custom lighting patterns
   - Command format: Unknown (requires hardware testing)
   - Priority: Medium

---

## Architecture Recommendations

### Option 1: Inheritance (❌ Not Recommended)

```python
class GoveePacket:
    """Base class for all models."""
    @staticmethod
    def power(on: bool) -> bytes: ...

class H6008Packet(GoveePacket):
    """Inherits everything from base."""
    pass  # Identical to H6006

class H6009Packet(GoveePacket):
    """Adds music sync."""
    @staticmethod
    def music_mode(enabled: bool) -> bytes: ...

class H6003Packet(GoveePacket):
    """No color temp support."""
    # How to disable color_temp()? Delete it?
```

**Problems:**
- Hard to disable features (H6003 color temp)
- Encourages code duplication
- Tight coupling between models
- Difficult to test feature combinations

**Verdict:** ❌ Avoid inheritance

---

### Option 2: Factory Pattern (❌ Not Recommended)

```python
def create_packet_builder(model: str) -> GoveePacket:
    if model == "H6006":
        return GoveePacket(has_color_temp=True, has_music=False)
    elif model == "H6008":
        return GoveePacket(has_color_temp=True, has_music=False)
    elif model == "H6009":
        return GoveePacket(has_color_temp=True, has_music=True)
    elif model == "H6003":
        return GoveePacket(has_color_temp=False, has_music=False)
```

**Problems:**
- Runtime complexity for compile-time decisions
- Feature flags pollute the base class
- Hard to type-check capabilities
- Testing requires mocking factory

**Verdict:** ❌ Overkill for this use case

---

### Option 3: Composition with Shared Base (✅ **RECOMMENDED**)

**Architecture:**

```python
# Shared base packet builder (100% reusable)
class GoveePacketBase:
    """Shared packet builder for all Govee H60xx models."""

    @staticmethod
    def _build_frame(cmd: int, payload: list[int]) -> bytes:
        """Build 20-byte command packet with XOR checksum."""
        # Shared implementation

    @staticmethod
    def power(on: bool) -> bytes:
        """Power command - identical across all models."""
        return GoveePacketBase._build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        """Brightness command - identical across all models."""
        return GoveePacketBase._build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        """RGB color command - identical across all models."""
        return GoveePacketBase._build_frame(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int, min_k: int = 2700, max_k: int = 6500) -> bytes:
        """Color temp command - used by H6006/H6008/H6009 (not H6003)."""
        kelvin = max(min_k, min(max_k, kelvin))
        warm = round((max_k - kelvin) / (max_k - min_k) * 255)
        cold = 255 - warm
        return GoveePacketBase._build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])


# Model-specific protocol classes (just capability metadata + extensions)
class H6006Protocol:
    """Protocol for Govee H6006 (RGBWW, 800 lm)."""

    MODEL_NAME = "H6006"
    DISCOVERY_PREFIX = "ihoment_H6006"
    HAS_COLOR_TEMP = True
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False
    MIN_KELVIN = 2700
    MAX_KELVIN = 6500

    # Reuse base packet builder
    power = GoveePacketBase.power
    brightness = GoveePacketBase.brightness
    color_rgb = GoveePacketBase.color_rgb
    color_temp = staticmethod(lambda k: GoveePacketBase.color_temp(k, 2700, 6500))


class H6008Protocol:
    """Protocol for Govee H6008 (RGBWW, 800 lm)."""

    MODEL_NAME = "H6008"
    DISCOVERY_PREFIX = "ihoment_H6008"
    HAS_COLOR_TEMP = True
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False
    MIN_KELVIN = 2700
    MAX_KELVIN = 6500

    # Identical to H6006
    power = GoveePacketBase.power
    brightness = GoveePacketBase.brightness
    color_rgb = GoveePacketBase.color_rgb
    color_temp = staticmethod(lambda k: GoveePacketBase.color_temp(k, 2700, 6500))


class H6009Protocol:
    """Protocol for Govee H6009 (RGBWW, 1200 lm, music sync, 54 scenes)."""

    MODEL_NAME = "H6009"
    DISCOVERY_PREFIX = "ihoment_H6009"
    HAS_COLOR_TEMP = True
    HAS_MUSIC_SYNC = True
    HAS_SCENE_MODES = True
    SCENE_COUNT = 54
    MIN_KELVIN = 2700
    MAX_KELVIN = 6500

    # Reuse base commands
    power = GoveePacketBase.power
    brightness = GoveePacketBase.brightness
    color_rgb = GoveePacketBase.color_rgb
    color_temp = staticmethod(lambda k: GoveePacketBase.color_temp(k, 2700, 6500))

    # H6009-specific extensions
    @staticmethod
    def music_sync(enabled: bool) -> bytes:
        """Enable/disable music sync mode (H6009 only)."""
        # TODO: Discover command format via hardware testing
        raise NotImplementedError("Music sync command requires hardware verification")

    @staticmethod
    def scene_mode(scene_id: int) -> bytes:
        """Select scene mode (1-54) (H6009 only)."""
        # TODO: Discover command format via hardware testing
        raise NotImplementedError("Scene mode command requires hardware verification")


class H6003Protocol:
    """Protocol for Govee H6003 (RGB-only, no color temp)."""

    MODEL_NAME = "H6003"
    DISCOVERY_PREFIX = "ihoment_H6003"
    HAS_COLOR_TEMP = False  # RGB-only (needs hardware verification)
    HAS_MUSIC_SYNC = False
    HAS_SCENE_MODES = False

    # Reuse base commands (except color_temp)
    power = GoveePacketBase.power
    brightness = GoveePacketBase.brightness
    color_rgb = GoveePacketBase.color_rgb
    # color_temp NOT included - H6003 may not support it
```

**Benefits:**
- ✅ **Maximum code reuse** - `GoveePacketBase` is 100% shared
- ✅ **Clear capability flags** - `HAS_COLOR_TEMP`, `HAS_MUSIC_SYNC`, etc.
- ✅ **Type-safe** - Each protocol class defines exactly what it supports
- ✅ **Easy to test** - Test `GoveePacketBase` once, verify capabilities per model
- ✅ **Easy to extend** - Add H6009 music sync without touching H6006/H6008
- ✅ **No runtime overhead** - Static methods, no dynamic dispatch
- ✅ **Discovery-friendly** - `DISCOVERY_PREFIX` per model for config flow

**Usage in GoveeAPI:**

```python
class GoveeAPI:
    def __init__(self, ble_device: BLEDevice, protocol: type, ...):
        self._protocol = protocol

    async def set_power(self, on: bool) -> None:
        await self._write(self._protocol.power(on))

    async def set_color_temp(self, kelvin: int) -> None:
        if not self._protocol.HAS_COLOR_TEMP:
            raise NotImplementedError(f"{self._protocol.MODEL_NAME} does not support color temperature")
        await self._write(self._protocol.color_temp(kelvin))
```

**Usage in Light Entity:**

```python
class GoveeLight(LightEntity):
    def __init__(self, coordinator: GoveeCoordinator, protocol: type):
        self._protocol = protocol

    @property
    def supported_features(self) -> int:
        features = SUPPORT_COLOR | SUPPORT_BRIGHTNESS
        if self._protocol.HAS_COLOR_TEMP:
            features |= SUPPORT_COLOR_TEMP
        return features

    @property
    def min_color_temp_kelvin(self) -> int | None:
        if self._protocol.HAS_COLOR_TEMP:
            return self._protocol.MIN_KELVIN
        return None
```

---

## Implementation Plan

### Phase 1: Refactor Existing Code (H6006)

1. **Extract shared base class**
   - Move `_build_frame`, `power`, `brightness`, `color_rgb` to `GoveePacketBase`
   - Create `H6006Protocol` that wraps `GoveePacketBase`
   - Update `GoveeAPI` to accept protocol class parameter
   - Update all tests to use new structure
   - **Goal:** No behavior change, just reorganization

2. **Add protocol capability system**
   - Add `HAS_COLOR_TEMP`, `MIN_KELVIN`, `MAX_KELVIN` to `H6006Protocol`
   - Update `GoveeLight` to check capabilities dynamically
   - Test that H6006 functionality remains unchanged

### Phase 2: Add H6008 and H6009 (Expected to be identical to H6006)

1. **Create H6008Protocol class**
   - Copy capability flags from H6006
   - Reuse all base commands
   - Update `DISCOVERY_PREFIX` to `"ihoment_H6008"`
   - Add test suite (copy H6006 tests, update model name)

2. **Create H6009Protocol class**
   - Copy capability flags from H6006
   - Add `HAS_MUSIC_SYNC = True`, `HAS_SCENE_MODES = True`
   - Reuse all base commands
   - Add stub methods for `music_sync()` and `scene_mode()` (raise `NotImplementedError`)
   - Update `DISCOVERY_PREFIX` to `"ihoment_H6009"`
   - Add test suite

3. **Update config flow**
   - Detect model from BLE device name
   - Map to appropriate protocol class:
     - `ihoment_H6006_*` → `H6006Protocol`
     - `ihoment_H6008_*` → `H6008Protocol`
     - `ihoment_H6009_*` → `H6009Protocol`
   - Pass protocol class to `GoveeAPI` and `GoveeCoordinator`

### Phase 3: Add H6003 (Conditional Color Temp)

1. **Create H6003Protocol class**
   - Set `HAS_COLOR_TEMP = False` (tentative - verify with hardware)
   - Reuse power, brightness, RGB commands
   - Do NOT include `color_temp` method
   - Update `DISCOVERY_PREFIX` to `"ihoment_H6003"`
   - Add test suite

2. **Test capability flags**
   - Verify `GoveeLight.supported_features` excludes `SUPPORT_COLOR_TEMP` for H6003
   - Verify `min_color_temp_kelvin` returns `None` for H6003
   - Verify Home Assistant UI hides color temp slider for H6003

### Phase 4: Hardware Verification

For each new model (H6008, H6009, H6003):

1. **Discovery test**
   - Verify BLE advertising name matches expected prefix
   - Confirm GATT UUIDs match H6006

2. **Basic command test**
   - Power on/off
   - Brightness control
   - RGB color control

3. **Color temp test**
   - Send color temp commands (H6008, H6009)
   - Verify H6003 behavior (does it ignore? error? simulate with RGB?)

4. **Advanced feature discovery (H6009)**
   - Reverse engineer music sync command
   - Reverse engineer scene selection command
   - Update `H6009Protocol.music_sync()` and `H6009Protocol.scene_mode()`

5. **Edge case testing**
   - Invalid checksums
   - Out-of-range values
   - Connection recovery

---

## File Structure

Recommended file organization:

```
custom_components/govee_h6006/
├── protocols/
│   ├── __init__.py           # Export all protocol classes
│   ├── base.py               # GoveePacketBase (shared code)
│   ├── h6006.py              # H6006Protocol
│   ├── h6008.py              # H6008Protocol
│   ├── h6009.py              # H6009Protocol
│   └── h6003.py              # H6003Protocol
├── api.py                    # GoveeAPI (protocol-agnostic)
├── coordinator.py            # GoveeCoordinator (protocol-agnostic)
├── config_flow.py            # Auto-discovery + protocol detection
├── light.py                  # GoveeLight (checks protocol.HAS_* flags)
├── const.py                  # Shared UUIDs, domain name
└── ...

tests/
├── protocols/
│   ├── test_base.py          # Test GoveePacketBase
│   ├── test_h6006.py         # Test H6006Protocol
│   ├── test_h6008.py         # Test H6008Protocol
│   ├── test_h6009.py         # Test H6009Protocol
│   └── test_h6003.py         # Test H6003Protocol
└── ...
```

**Alternative (simpler):** Keep all protocol classes in a single file:

```
custom_components/govee_h6006/
├── protocols.py              # All protocol classes (base + H6006/H6008/H6009/H6003)
├── api.py                    # GoveeAPI
├── coordinator.py            # GoveeCoordinator
└── ...
```

**Recommendation:** Start with single-file approach (`protocols.py`) since code is small. Split into `protocols/` directory if H6009 advanced features add significant complexity.

---

## Testing Strategy

### Unit Tests (Protocol Classes)

Test `GoveePacketBase` extensively since it's shared:

```python
def test_build_frame_checksum():
    """Verify XOR checksum calculation."""
    packet = GoveePacketBase.power(True)
    assert len(packet) == 20
    assert packet[19] == (packet[0] ^ packet[1] ^ ... ^ packet[18])

def test_power_command():
    """Power on/off generate correct packets."""
    assert GoveePacketBase.power(True) == bytes([0x33, 0x01, 0x01, ...])
    assert GoveePacketBase.power(False) == bytes([0x33, 0x01, 0x00, ...])

def test_brightness_clamping():
    """Brightness values are clamped to 0-255."""
    assert GoveePacketBase.brightness(-10) == GoveePacketBase.brightness(0)
    assert GoveePacketBase.brightness(300) == GoveePacketBase.brightness(255)

def test_color_temp_range():
    """Color temp respects min/max kelvin."""
    packet_2700 = GoveePacketBase.color_temp(2700, 2700, 6500)
    packet_6500 = GoveePacketBase.color_temp(6500, 2700, 6500)
    # Verify warm/cold byte calculations
```

Test each protocol class for capability flags:

```python
def test_h6006_capabilities():
    assert H6006Protocol.HAS_COLOR_TEMP is True
    assert H6006Protocol.HAS_MUSIC_SYNC is False
    assert H6006Protocol.MIN_KELVIN == 2700
    assert H6006Protocol.DISCOVERY_PREFIX == "ihoment_H6006"

def test_h6003_capabilities():
    assert H6003Protocol.HAS_COLOR_TEMP is False  # Tentative
    assert not hasattr(H6003Protocol, 'color_temp')  # Should not exist
```

### Integration Tests (GoveeAPI + Protocol)

Test that `GoveeAPI` works with different protocol classes:

```python
@pytest.mark.parametrize("protocol", [H6006Protocol, H6008Protocol, H6009Protocol])
async def test_api_with_protocol(protocol):
    """Verify GoveeAPI works with different protocols."""
    api = GoveeAPI(mock_ble_device, protocol, ...)
    await api.set_power(True)
    await api.set_brightness(128)
    await api.set_color_rgb(255, 0, 0)
    if protocol.HAS_COLOR_TEMP:
        await api.set_color_temp(4600)

async def test_h6003_color_temp_error():
    """H6003 should raise error when calling color_temp."""
    api = GoveeAPI(mock_ble_device, H6003Protocol, ...)
    with pytest.raises(NotImplementedError):
        await api.set_color_temp(4600)
```

### Hardware Verification Tests

For each new model, create a manual test checklist:

```python
# tests/hardware/test_h6008_hardware.py (manual test - not CI)
async def test_h6008_discovery():
    """Manual: Verify H6008 advertises with expected name."""
    # Scan for BLE devices
    # Confirm name starts with "ihoment_H6008"

async def test_h6008_power_control():
    """Manual: Send power commands to real H6008 device."""
    # Connect to H6008
    # Send power on → verify LED turns on
    # Send power off → verify LED turns off
```

---

## Migration Path for Users

Since we're expanding from single-model (H6006) to multi-model support:

1. **Existing H6006 users:** No changes required
   - Config flow still detects `ihoment_H6006_*` devices
   - Protocol class is selected automatically
   - All existing functionality preserved

2. **New H6008/H6009/H6003 users:** Seamless auto-detection
   - Discovery flow detects device name
   - Maps to appropriate protocol class
   - User sees model-specific capabilities in UI

3. **Upgrading existing installations:**
   - No breaking changes to H6006 protocol
   - New models appear in discovery automatically
   - README updated to list all supported models

---

## Summary

**Code Reuse:**
- **100% shared:** Packet builder, power/brightness/RGB commands, GATT UUIDs, connection logic
- **Conditional:** Color temperature (exclude H6003 if RGB-only)
- **Model-specific:** Music sync and scene modes (H6009 only)

**Recommended Architecture:**
- **Composition with shared base class** (`GoveePacketBase` + model protocol classes)
- Clear capability flags (`HAS_COLOR_TEMP`, `HAS_MUSIC_SYNC`, etc.)
- Protocol class passed to API/coordinator/light entity
- Zero runtime overhead (static methods)

**Implementation Priority:**
1. Refactor H6006 to use new structure (no behavior change)
2. Add H6008 and H6009 (expected identical to H6006 for basic features)
3. Add H6003 (conditional color temp support)
4. Hardware verification for all models
5. Reverse engineer H6009 advanced features (music sync, scenes)

**Next Steps:**
- Acquire hardware for H6008, H6009, H6003
- Verify BLE advertising names match expected prefixes
- Confirm basic commands work identically
- Test H6003 color temp support (RGB-only vs RGBWW)
- Reverse engineer H6009 music sync and scene mode commands
