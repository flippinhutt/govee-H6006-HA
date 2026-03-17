"""Tests for H6009Protocol BLE packet generation.

This test suite verifies that the H6009 protocol implementation generates correct
20-byte BLE command packets with proper checksums and value clamping.
"""

from custom_components.govee_h6006.protocols import H6009Protocol


def test_power_on_packet():
    """Power ON command should use cmd=0x01, payload=0x01"""
    frame = H6009Protocol.power(True)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND head
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x01       # ON
    assert _valid_checksum(frame)


def test_power_off_packet():
    """Power OFF command should use cmd=0x01, payload=0x00"""
    frame = H6009Protocol.power(False)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND head
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x00       # OFF
    assert _valid_checksum(frame)


def test_brightness_packet():
    """Brightness command should use cmd=0x04 with brightness value"""
    frame = H6009Protocol.brightness(128)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x04
    assert frame[2] == 128
    assert _valid_checksum(frame)


def test_brightness_clamps_to_range():
    """Brightness values should clamp to [0, 255] range"""
    assert H6009Protocol.brightness(-1)[2] == 0    # clamps to 0
    assert H6009Protocol.brightness(256)[2] == 255  # clamps to 255
    assert H6009Protocol.brightness(0)[2] == 0      # boundary
    assert H6009Protocol.brightness(255)[2] == 255  # boundary


def test_rgb_packet():
    """RGB command should use cmd=0x05, mode=0x02, with RGB values"""
    frame = H6009Protocol.color_rgb(255, 0, 128)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 255        # R
    assert frame[4] == 0          # G
    assert frame[5] == 128        # B
    assert _valid_checksum(frame)


def test_rgb_clamps_to_range():
    """RGB values should clamp to [0, 255] range"""
    # Test negative values clamp to 0
    frame = H6009Protocol.color_rgb(-1, -50, -100)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 0    # B clamps to 0
    assert _valid_checksum(frame)

    # Test values > 255 clamp to 255
    frame = H6009Protocol.color_rgb(256, 300, 500)
    assert frame[3] == 255  # R clamps to 255
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)

    # Test boundary values
    frame = H6009Protocol.color_rgb(0, 255, 128)
    assert frame[3] == 0    # R at minimum
    assert frame[4] == 255  # G at maximum
    assert frame[5] == 128  # B in range
    assert _valid_checksum(frame)


def test_rgb_clamps_individual_channels():
    """Each RGB channel should clamp independently"""
    # R negative, G over max, B in range
    frame = H6009Protocol.color_rgb(-10, 300, 128)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 128  # B unchanged
    assert _valid_checksum(frame)

    # R in range, G negative, B over max
    frame = H6009Protocol.color_rgb(100, -5, 260)
    assert frame[3] == 100  # R unchanged
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)


def test_color_temp_packet_warm():
    """Color temp at 2700K (warmest) should have warm=255, cold=0"""
    frame = H6009Protocol.color_temp(2700)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 0xFF       # white R
    assert frame[4] == 0xFF       # white G
    assert frame[5] == 0xFF       # white B
    assert frame[6] == 0x01       # white sub-mode
    assert frame[7] == 255        # warm = max at 2700K
    assert frame[8] == 0          # cold = 0 at 2700K
    assert _valid_checksum(frame)


def test_color_temp_packet_cold():
    """Color temp at 6500K (coldest) should have warm=0, cold=255"""
    frame = H6009Protocol.color_temp(6500)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[7] == 0          # warm = 0 at 6500K
    assert frame[8] == 255        # cold = max at 6500K
    assert _valid_checksum(frame)


def test_color_temp_clamps_below_minimum():
    """Values below 2700K should clamp to 2700K (warmest)"""
    frame = H6009Protocol.color_temp(2000)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 0xFF       # white R
    assert frame[4] == 0xFF       # white G
    assert frame[5] == 0xFF       # white B
    assert frame[6] == 0x01       # white sub-mode
    assert frame[7] == 255        # warm = max (clamped to 2700K)
    assert frame[8] == 0          # cold = 0 (clamped to 2700K)
    assert _valid_checksum(frame)


def test_color_temp_clamps_above_maximum():
    """Values above 6500K should clamp to 6500K (coldest)"""
    frame = H6009Protocol.color_temp(7000)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 0xFF       # white R
    assert frame[4] == 0xFF       # white G
    assert frame[5] == 0xFF       # white B
    assert frame[6] == 0x01       # white sub-mode
    assert frame[7] == 0          # warm = 0 (clamped to 6500K)
    assert frame[8] == 255        # cold = max (clamped to 6500K)
    assert _valid_checksum(frame)


def test_color_temp_midrange():
    """Mid-range value (4600K) should have balanced warm/cold"""
    frame = H6009Protocol.color_temp(4600)
    assert len(frame) == 20
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 0xFF       # white R
    assert frame[4] == 0xFF       # white G
    assert frame[5] == 0xFF       # white B
    assert frame[6] == 0x01       # white sub-mode
    # 4600K is exactly halfway between 2700K and 6500K
    # warm = (6500 - 4600) / (6500 - 2700) * 255 = 1900/3800 * 255 = 127.5 -> 128
    # cold = 255 - 128 = 127
    assert frame[7] == 128        # warm
    assert frame[8] == 127        # cold
    assert _valid_checksum(frame)


def test_color_temp_extreme_values():
    """Extremely out of range values should still clamp correctly"""
    # Very low value
    frame_low = H6009Protocol.color_temp(0)
    assert len(frame_low) == 20
    assert frame_low[7] == 255    # warm = max
    assert frame_low[8] == 0      # cold = 0
    assert _valid_checksum(frame_low)

    # Very high value
    frame_high = H6009Protocol.color_temp(10000)
    assert len(frame_high) == 20
    assert frame_high[7] == 0     # warm = 0
    assert frame_high[8] == 255   # cold = max
    assert _valid_checksum(frame_high)


def test_checksum_is_xor_of_first_19_bytes():
    """Checksum should be XOR of all bytes before it"""
    frame = H6009Protocol.power(True)
    expected = 0
    for b in frame[:19]:
        expected ^= b
    assert frame[19] == expected


def test_protocol_capabilities():
    """H6009 should have correct capability flags"""
    assert H6009Protocol.MODEL_NAME == "H6009"
    assert H6009Protocol.DISCOVERY_PREFIX == "ihoment_H6009"
    assert H6009Protocol.HAS_COLOR_TEMP is True
    assert H6009Protocol.HAS_MUSIC_SYNC is True
    assert H6009Protocol.HAS_SCENE_MODES is True
    assert H6009Protocol.MIN_KELVIN == 2700
    assert H6009Protocol.MAX_KELVIN == 6500


def _valid_checksum(frame: bytes) -> bool:
    """Validate XOR checksum of a 20-byte packet"""
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor
