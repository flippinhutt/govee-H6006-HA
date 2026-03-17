"""Test H6003Protocol command builders."""

from custom_components.govee_h6006.protocols import H6003Protocol


def test_h6003_power_on():
    """Test H6003 power on command."""
    packet = H6003Protocol.power(True)
    assert len(packet) == 20
    assert packet[0] == 0x33  # Command head
    assert packet[1] == 0x01  # Power command
    assert packet[2] == 0x01  # On
    assert _valid_checksum(packet)


def test_h6003_power_off():
    """Test H6003 power off command."""
    packet = H6003Protocol.power(False)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x01
    assert packet[2] == 0x00  # Off
    assert _valid_checksum(packet)


def test_h6003_brightness():
    """Test H6003 brightness command."""
    packet = H6003Protocol.brightness(128)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x04  # Brightness command
    assert packet[2] == 128
    assert _valid_checksum(packet)


def test_h6003_brightness_clamps_to_range():
    """Test H6003 brightness value clamping."""
    assert H6003Protocol.brightness(-1)[2] == 0    # clamps to 0
    assert H6003Protocol.brightness(256)[2] == 255  # clamps to 255
    assert H6003Protocol.brightness(0)[2] == 0      # boundary
    assert H6003Protocol.brightness(255)[2] == 255  # boundary


def test_h6003_color_rgb():
    """Test H6003 RGB color command."""
    packet = H6003Protocol.color_rgb(255, 128, 64)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x05  # Color command
    assert packet[2] == 0x02  # RGB mode
    assert packet[3] == 255   # Red
    assert packet[4] == 128   # Green
    assert packet[5] == 64    # Blue
    assert _valid_checksum(packet)


def test_h6003_rgb_clamps_to_range():
    """RGB values should clamp to [0, 255] range"""
    # Test negative values clamp to 0
    frame = H6003Protocol.color_rgb(-1, -50, -100)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 0    # B clamps to 0
    assert _valid_checksum(frame)

    # Test values > 255 clamp to 255
    frame = H6003Protocol.color_rgb(256, 300, 500)
    assert frame[3] == 255  # R clamps to 255
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)

    # Test boundary values
    frame = H6003Protocol.color_rgb(0, 255, 128)
    assert frame[3] == 0    # R at minimum
    assert frame[4] == 255  # G at maximum
    assert frame[5] == 128  # B in range
    assert _valid_checksum(frame)


def test_h6003_rgb_clamps_individual_channels():
    """Each RGB channel should clamp independently"""
    # R negative, G over max, B in range
    frame = H6003Protocol.color_rgb(-10, 300, 128)
    assert frame[3] == 0    # R clamps to 0
    assert frame[4] == 255  # G clamps to 255
    assert frame[5] == 128  # B unchanged
    assert _valid_checksum(frame)

    # R in range, G negative, B over max
    frame = H6003Protocol.color_rgb(100, -5, 260)
    assert frame[3] == 100  # R unchanged
    assert frame[4] == 0    # G clamps to 0
    assert frame[5] == 255  # B clamps to 255
    assert _valid_checksum(frame)


def test_h6003_capabilities():
    """Test H6003 capability flags."""
    assert H6003Protocol.MODEL_NAME == "H6003"
    assert H6003Protocol.DISCOVERY_PREFIX == "ihoment_H6003"
    assert H6003Protocol.HAS_COLOR_TEMP is False
    assert H6003Protocol.HAS_MUSIC_SYNC is False
    assert H6003Protocol.HAS_SCENE_MODES is False


def test_h6003_checksum_is_xor_of_first_19_bytes():
    """Test XOR checksum calculation."""
    frame = H6003Protocol.power(True)
    expected = 0
    for b in frame[:19]:
        expected ^= b
    assert frame[19] == expected


def _valid_checksum(frame: bytes) -> bool:
    """Verify that a packet has a valid XOR checksum."""
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor
