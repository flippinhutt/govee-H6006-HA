import pytest
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
