"""Tests for H6008Protocol BLE packet generation and reply parsing.

Expected frames were captured from a real H6008 (hardware 1.02.01): the bulb accepted
every command frame below with status 0x00, and the replies are what it sent back.
"""

from custom_components.govee_h6006.protocols import H6006Protocol, H6008Protocol


def _frame(hex_bytes: str) -> bytes:
    """Build a 20-byte frame from its leading bytes, zero padding and XOR checksum."""
    body = list(bytes.fromhex(hex_bytes))
    body += [0] * (19 - len(body))
    checksum = 0
    for b in body:
        checksum ^= b
    return bytes(body + [checksum])


def test_power_on_packet():
    assert H6008Protocol.power(True) == _frame("33 01 01")


def test_power_off_packet():
    assert H6008Protocol.power(False) == _frame("33 01 00")


def test_brightness_is_sent_as_percent():
    """HA's 0-255 is sent as 1-100: the bulb stores raw values and expects a percentage."""
    assert H6008Protocol.brightness(255) == _frame("33 04 64")
    assert H6008Protocol.brightness(51) == _frame("33 04 14")  # 20 %, accepted by the bulb
    assert H6008Protocol.brightness(128)[2] == 50


def test_brightness_clamps_to_1_100():
    assert H6008Protocol.brightness(0)[2] == 1
    assert H6008Protocol.brightness(1)[2] == 1
    assert H6008Protocol.brightness(-5)[2] == 1
    assert H6008Protocol.brightness(300)[2] == 100


def test_rgb_packet_uses_mode_0d():
    """The bulb rejects the H6006's mode 0x02 (status 0x01) and accepts 0x0d."""
    assert H6008Protocol.color_rgb(0, 255, 0) == _frame("33 05 0d 00 ff 00")


def test_rgb_clamps_individual_channels():
    frame = H6008Protocol.color_rgb(-10, 300, 128)
    assert frame[2:6] == bytes([0x0D, 0, 255, 128])


def test_color_temp_packet_matches_hardware_capture():
    """2700 K frame as accepted by the bulb: 0d, tint, Kelvin big-endian, tint."""
    assert H6008Protocol.color_temp(2700) == _frame("33 05 0d ff a7 57 0a 8c ff a7 57")


def test_color_temp_layout():
    frame = H6008Protocol.color_temp(6500)
    assert frame[:3] == bytes([0x33, 0x05, 0x0D])
    assert frame[6] << 8 | frame[7] == 6500
    assert frame[3:6] == frame[8:11]  # tint is repeated


def test_color_temp_rounds_to_100k_and_clamps():
    def kelvin(frame: bytes) -> int:
        return frame[6] << 8 | frame[7]

    assert kelvin(H6008Protocol.color_temp(2750)) == 2800
    assert kelvin(H6008Protocol.color_temp(3449)) == 3400
    assert kelvin(H6008Protocol.color_temp(2000)) == 2700
    assert kelvin(H6008Protocol.color_temp(10000)) == 6500


def test_color_temp_tint_gets_warmer_with_lower_kelvin():
    warm = H6008Protocol.color_temp(2700)
    cool = H6008Protocol.color_temp(6500)
    assert warm[3] == cool[3] == 0xFF  # red saturates below 6600 K
    assert warm[5] < cool[5]  # less blue when warm


def test_parse_brightness_reply_is_percent():
    assert H6008Protocol.parse_brightness(0x64) == 255
    assert H6008Protocol.parse_brightness(0x14) == 51
    assert H6008Protocol.parse_brightness(0xFF) == 255  # out-of-range values set by other clients


def test_brightness_round_trip_stays_close():
    for value in range(1, 256):
        sent = H6008Protocol.brightness(value)[2]
        assert abs(H6008Protocol.parse_brightness(sent) - value) <= 2


def test_parse_color_temp_reply():
    """Reply seen in white mode at 3500 K (tint ff c9 87)."""
    assert H6008Protocol.parse_color(_frame("aa 05 0d ff c9 87 0d ac")) == (None, 3500)


def test_parse_rgb_reply():
    """Reply after setting green: Kelvin bytes are zero in RGB mode."""
    assert H6008Protocol.parse_color(_frame("aa 05 0d 00 ff 00")) == ((0, 255, 0), None)


def test_parse_color_ignores_other_modes():
    assert H6008Protocol.parse_color(_frame("aa 05 04 01")) is None


def test_h6006_parsing_unchanged():
    """The base parsing the H6006 uses keeps its 0-255 brightness and white-mode logic."""
    assert H6006Protocol.parse_brightness(0x80) == 0x80
    assert H6006Protocol.parse_color(_frame("aa 05 02 ff ff ff 01 00")) == (None, 6500)
    assert H6006Protocol.parse_color(_frame("aa 05 02 ff ff ff 01 ff")) == (None, 2700)
    assert H6006Protocol.parse_color(_frame("aa 05 02 10 20 30")) == ((0x10, 0x20, 0x30), None)


def test_protocol_capabilities():
    assert H6008Protocol.MODEL_NAME == "H6008"
    assert H6008Protocol.DISCOVERY_PREFIX == "ihoment_H6008"
    assert H6008Protocol.HAS_COLOR_TEMP is True
    assert H6008Protocol.HAS_MUSIC_SYNC is False
    assert H6008Protocol.HAS_SCENE_MODES is False
    assert H6008Protocol.MIN_KELVIN == 2700
    assert H6008Protocol.MAX_KELVIN == 6500
