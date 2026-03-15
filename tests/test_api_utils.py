from custom_components.govee_h6006.api_utils import GoveePacket


def test_power_on_packet():
    frame = GoveePacket.power(True)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND head
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x01       # ON
    assert _valid_checksum(frame)


def test_power_off_packet():
    frame = GoveePacket.power(False)
    assert frame[2] == 0x00
    assert _valid_checksum(frame)


def test_brightness_packet():
    frame = GoveePacket.brightness(128)
    assert frame[0] == 0x33
    assert frame[1] == 0x04
    assert frame[2] == 128
    assert _valid_checksum(frame)


def test_brightness_clamps_to_range():
    assert GoveePacket.brightness(-1)[2] == 0    # clamps to 0
    assert GoveePacket.brightness(256)[2] == 255  # clamps to 255
    assert GoveePacket.brightness(0)[2] == 0      # boundary
    assert GoveePacket.brightness(255)[2] == 255  # boundary


def test_rgb_packet():
    frame = GoveePacket.color_rgb(255, 0, 128)
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
    frame = GoveePacket.color_rgb(-1, -50, -100)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 0    # B clamps to 0
    assert _valid_checksum(frame)

    # Test values > 255 clamp to 255
    frame = GoveePacket.color_rgb(256, 300, 500)
    assert frame[3] == 255  # R clamps to 255
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)

    # Test boundary values
    frame = GoveePacket.color_rgb(0, 255, 128)
    assert frame[3] == 0    # R at minimum
    assert frame[4] == 255  # G at maximum
    assert frame[5] == 128  # B in range
    assert _valid_checksum(frame)


def test_rgb_clamps_individual_channels():
    """Each RGB channel should clamp independently"""
    # R negative, G over max, B in range
    frame = GoveePacket.color_rgb(-10, 300, 128)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 128  # B unchanged
    assert _valid_checksum(frame)

    # R in range, G negative, B over max
    frame = GoveePacket.color_rgb(100, -5, 260)
    assert frame[3] == 100  # R unchanged
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)


def test_color_temp_packet_warm():
    frame = GoveePacket.color_temp(2700)
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
    frame = GoveePacket.color_temp(6500)
    assert frame[7] == 0          # warm = 0 at 6500K
    assert frame[8] == 255        # cold = max at 6500K
    assert _valid_checksum(frame)


def test_color_temp_clamps_below_minimum():
    """Values below 2700K should clamp to 2700K (warmest)"""
    frame = GoveePacket.color_temp(2000)
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
    frame = GoveePacket.color_temp(7000)
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
    frame = GoveePacket.color_temp(4600)
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
    frame_low = GoveePacket.color_temp(0)
    assert frame_low[7] == 255    # warm = max
    assert frame_low[8] == 0      # cold = 0
    assert _valid_checksum(frame_low)

    # Very high value
    frame_high = GoveePacket.color_temp(10000)
    assert frame_high[7] == 0     # warm = 0
    assert frame_high[8] == 255   # cold = max
    assert _valid_checksum(frame_high)


def test_checksum_is_xor_of_first_19_bytes():
    frame = GoveePacket.power(True)
    expected = 0
    for b in frame[:19]:
        expected ^= b
    assert frame[19] == expected


def _valid_checksum(frame: bytes) -> bool:
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor
