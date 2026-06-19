from __future__ import annotations


MSP_API_VERSION = 1
MSP_STATUS = 101
MSP_RAW_GPS = 106
MSP_ATTITUDE = 108
MSP_ANALOG = 110
MSP_NAV_STATUS = 121
MSP_STATUS_EX = 150


def build_msp(command: int, payload: bytes | bytearray | list[int] = b"") -> bytes:
    body = bytes(payload)
    size = len(body)
    checksum = size ^ (command & 0xFF)

    for byte in body:
        checksum ^= byte

    return bytes([ord("$"), ord("M"), ord("<"), size, command & 0xFF]) + body + bytes([checksum])


def read_i16_le(payload: bytes, offset: int) -> int:
    value = payload[offset] | (payload[offset + 1] << 8)
    return value - 0x10000 if value & 0x8000 else value


def read_u16_le(payload: bytes, offset: int) -> int:
    return payload[offset] | (payload[offset + 1] << 8)


def read_i32_le(payload: bytes, offset: int) -> int:
    value = (
        payload[offset]
        | (payload[offset + 1] << 8)
        | (payload[offset + 2] << 16)
        | (payload[offset + 3] << 24)
    )
    return value - 0x100000000 if value & 0x80000000 else value
