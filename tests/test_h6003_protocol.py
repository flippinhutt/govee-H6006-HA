"""Test H6003Protocol command builders."""

from custom_components.govee_h6006.protocols import H6003Protocol


def test_h6003_power_on():
    """Test H6003 power on command."""
    packet = H6003Protocol.power(True)
    assert len(packet) == 20
    assert packet[0] == 0x33  # Command head
    assert packet[1] == 0x01  # Power command
    assert packet[2] == 0x01  # On


def test_h6003_power_off():
    """Test H6003 power off command."""
    packet = H6003Protocol.power(False)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x01
    assert packet[2] == 0x00  # Off


def test_h6003_brightness():
    """Test H6003 brightness command."""
    packet = H6003Protocol.brightness(128)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x04  # Brightness command
    assert packet[2] == 128


def test_h6003_brightness_clamp():
    """Test H6003 brightness value clamping."""
    # Test upper bound
    packet = H6003Protocol.brightness(300)
    assert packet[2] == 255

    # Test lower bound
    packet = H6003Protocol.brightness(-10)
    assert packet[2] == 0


def test_h6003_color_rgb():
    """Test H6003 RGB color command."""
    packet = H6003Protocol.color_rgb(255, 128, 64)
    assert len(packet) == 20
    assert packet[0] == 0x33
    assert packet[1] == 0x05  # Color command
    assert packet[2] == 0x02  # RGB mode
    assert packet[3] == 255  # Red
    assert packet[4] == 128  # Green
    assert packet[5] == 64   # Blue


def test_h6003_color_rgb_clamp():
    """Test H6003 RGB color value clamping."""
    packet = H6003Protocol.color_rgb(300, -10, 128)
    assert packet[3] == 255  # Clamped to max
    assert packet[4] == 0    # Clamped to min
    assert packet[5] == 128  # Normal


def test_h6003_capabilities():
    """Test H6003 capability flags."""
    assert H6003Protocol.MODEL_NAME == "H6003"
    assert H6003Protocol.DISCOVERY_PREFIX == "ihoment_H6003"
    assert H6003Protocol.HAS_COLOR_TEMP is False
    assert H6003Protocol.HAS_MUSIC_SYNC is False
    assert H6003Protocol.HAS_SCENE_MODES is False


def test_h6003_checksum():
    """Test H6003 packet checksum calculation."""
    packet = H6003Protocol.power(True)
    # Verify XOR checksum in last byte
    checksum = 0
    for b in packet[:-1]:
        checksum ^= b
    assert packet[-1] == (checksum & 0xFF)
