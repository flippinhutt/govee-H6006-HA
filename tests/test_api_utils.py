from custom_components.govee_h6006.protocols.h6006 import H6006Protocol


def test_power_on_packet():
    protocol = H6006Protocol()
    frame = protocol.build_power_packet(True)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND head
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x01       # ON
    assert _valid_checksum(frame)


def test_power_off_packet():
    protocol = H6006Protocol()
    frame = protocol.build_power_packet(False)
    assert frame[2] == 0x00
    assert _valid_checksum(frame)


def test_brightness_packet():
    protocol = H6006Protocol()
    frame = protocol.build_brightness_packet(128)
    assert frame[0] == 0x33
    assert frame[1] == 0x04
    assert frame[2] == 128
    assert _valid_checksum(frame)


def test_brightness_clamps_to_range():
    protocol = H6006Protocol()
    assert protocol.build_brightness_packet(-1)[2] == 0    # clamps to 0
    assert protocol.build_brightness_packet(256)[2] == 255  # clamps to 255
    assert protocol.build_brightness_packet(0)[2] == 0      # boundary
    assert protocol.build_brightness_packet(255)[2] == 255  # boundary


def test_rgb_packet():
    protocol = H6006Protocol()
    frame = protocol.build_color_rgb_packet(255, 0, 128)
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 255        # R
    assert frame[4] == 0          # G
    assert frame[5] == 128        # B
    assert _valid_checksum(frame)


def test_rgb_clamps_to_range():
    """RGB values should clamp to [0, 255] range"""
    protocol = H6006Protocol()
    # Test negative values clamp to 0
    frame = protocol.build_color_rgb_packet(-1, -50, -100)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 0    # B clamps to 0
    assert _valid_checksum(frame)

    # Test values > 255 clamp to 255
    frame = protocol.build_color_rgb_packet(256, 300, 500)
    assert frame[3] == 255  # R clamps to 255
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)

    # Test boundary values
    frame = protocol.build_color_rgb_packet(0, 255, 128)
    assert frame[3] == 0    # R at minimum
    assert frame[4] == 255  # G at maximum
    assert frame[5] == 128  # B in range
    assert _valid_checksum(frame)


def test_rgb_clamps_individual_channels():
    """Each RGB channel should clamp independently"""
    protocol = H6006Protocol()
    # R negative, G over max, B in range
    frame = protocol.build_color_rgb_packet(-10, 300, 128)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 128  # B unchanged
    assert _valid_checksum(frame)

    # R in range, G negative, B over max
    frame = protocol.build_color_rgb_packet(100, -5, 260)
    assert frame[3] == 100  # R unchanged
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)


def test_color_temp_packet_warm():
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(2700)
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
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(6500)
    assert frame[7] == 0          # warm = 0 at 6500K
    assert frame[8] == 255        # cold = max at 6500K
    assert _valid_checksum(frame)


def test_color_temp_clamps_below_minimum():
    """Values below 2700K should clamp to 2700K (warmest)"""
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(2000)
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
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(7000)
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
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(4600)
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
    protocol = H6006Protocol()
    # Very low value
    frame_low = protocol.build_color_temp_packet(0)
    assert frame_low[7] == 255    # warm = max
    assert frame_low[8] == 0      # cold = 0
    assert _valid_checksum(frame_low)

    # Very high value
    frame_high = protocol.build_color_temp_packet(10000)
    assert frame_high[7] == 0     # warm = 0
    assert frame_high[8] == 255   # cold = max
    assert _valid_checksum(frame_high)


def test_checksum_is_xor_of_first_19_bytes():
    protocol = H6006Protocol()
    frame = protocol.build_power_packet(True)
    expected = 0
    for b in frame[:19]:
        expected ^= b
    assert frame[19] == expected


def _valid_checksum(frame: bytes) -> bool:
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor
