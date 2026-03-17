"""Tests for H6006Protocol implementation."""
from custom_components.govee_h6006.protocols.h6006 import H6006Protocol


def test_power_on_packet():
    protocol = H6006Protocol()
    frame = protocol.build_power_packet(True)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x01       # ON
    assert _valid_checksum(frame)


def test_power_off_packet():
    protocol = H6006Protocol()
    frame = protocol.build_power_packet(False)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x00       # OFF
    assert _valid_checksum(frame)


def test_brightness_packet():
    protocol = H6006Protocol()
    frame = protocol.build_brightness_packet(128)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x04       # BRIGHTNESS cmd
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
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
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
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
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
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
    assert frame[7] == 0          # warm = 0 at 6500K
    assert frame[8] == 255        # cold = max at 6500K
    assert _valid_checksum(frame)


def test_color_temp_clamps_below_minimum():
    """Values below 2700K should clamp to 2700K (warmest)"""
    protocol = H6006Protocol()
    frame = protocol.build_color_temp_packet(2000)
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
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
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
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
    assert frame[0] == 0x33       # COMMAND_HEAD
    assert frame[1] == 0x05       # COLOR cmd
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


def test_parse_notification_power_on():
    """Parse power ON notification"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0x01, 0x01] + [0] * 17)
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is not None
    assert result["power"] is True


def test_parse_notification_power_off():
    """Parse power OFF notification"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0x01, 0x00] + [0] * 17)
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is not None
    assert result["power"] is False


def test_parse_notification_brightness():
    """Parse brightness notification"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0x04, 128] + [0] * 17)
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is not None
    assert result["brightness"] == 128


def test_parse_notification_rgb_color():
    """Parse RGB color notification"""
    protocol = H6006Protocol()
    # RGB mode: cmd=0x05, mode=0x02, R=255, G=0, B=128
    frame = bytearray([0xAA, 0x05, 0x02, 255, 0, 128] + [0] * 14)
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is not None
    assert result["color_rgb"] == (255, 0, 128)


def test_parse_notification_color_temp():
    """Parse color temperature notification (white mode)"""
    protocol = H6006Protocol()
    # White mode: cmd=0x05, mode=0x02, R=0xFF, G=0xFF, B=0xFF, submode=0x01, warm=255, cold=0
    frame = bytearray([0xAA, 0x05, 0x02, 0xFF, 0xFF, 0xFF, 0x01, 255, 0] + [0] * 11)
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is not None
    # warm=255, cold=0 -> 2700K (warmest)
    assert result["color_temp"] == 2700


def test_parse_notification_invalid_checksum():
    """Invalid checksum should return None"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0x01, 0x01] + [0] * 17)
    frame[19] = 0xFF  # Wrong checksum

    result = protocol.parse_notification(frame)
    assert result is None


def test_parse_notification_wrong_head():
    """Wrong packet head should return None"""
    protocol = H6006Protocol()
    frame = bytearray([0x33, 0x01, 0x01] + [0] * 17)  # 0x33 is COMMAND_HEAD, not REQUEST_HEAD
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is None


def test_parse_notification_too_short():
    """Packet shorter than 20 bytes should return None"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0x01, 0x01])

    result = protocol.parse_notification(frame)
    assert result is None


def test_parse_notification_unknown_command():
    """Unknown command should return None (empty result dict)"""
    protocol = H6006Protocol()
    frame = bytearray([0xAA, 0xFF, 0x00] + [0] * 17)  # Unknown command 0xFF
    frame[19] = _calculate_checksum(frame[:19])

    result = protocol.parse_notification(frame)
    assert result is None


def test_all_packets_are_20_bytes():
    """All packet building methods should return exactly 20 bytes"""
    protocol = H6006Protocol()

    assert len(protocol.build_power_packet(True)) == 20
    assert len(protocol.build_power_packet(False)) == 20
    assert len(protocol.build_brightness_packet(128)) == 20
    assert len(protocol.build_color_rgb_packet(255, 128, 0)) == 20
    assert len(protocol.build_color_temp_packet(4600)) == 20


def test_protocol_is_stateless():
    """Protocol instances should be stateless - same inputs produce same outputs"""
    protocol1 = H6006Protocol()
    protocol2 = H6006Protocol()

    # Same method calls should produce identical packets
    assert protocol1.build_power_packet(True) == protocol2.build_power_packet(True)
    assert protocol1.build_brightness_packet(100) == protocol2.build_brightness_packet(100)
    assert protocol1.build_color_rgb_packet(255, 128, 64) == protocol2.build_color_rgb_packet(255, 128, 64)
    assert protocol1.build_color_temp_packet(4600) == protocol2.build_color_temp_packet(4600)


def _valid_checksum(frame: bytes) -> bool:
    """Validate XOR checksum of a packet."""
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor


def _calculate_checksum(data: bytearray) -> int:
    """Calculate XOR checksum for notification packet."""
    xor = 0
    for b in data:
        xor ^= b
    return xor & 0xFF
