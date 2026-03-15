from __future__ import annotations

from .const import MAX_KELVIN, MIN_KELVIN

_PACKET_LEN = 20
_CMD_HEAD = 0x33


def _build_frame(cmd: int, payload: list[int]) -> bytes:
    frame = [_CMD_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)


class GoveePacket:
    @staticmethod
    def power(on: bool) -> bytes:
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return _build_frame(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        kelvin = max(MIN_KELVIN, min(MAX_KELVIN, kelvin))
        warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
        cold = 255 - warm
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
