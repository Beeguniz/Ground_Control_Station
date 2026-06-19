from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.core.msp import (
    MSP_ANALOG,
    MSP_API_VERSION,
    MSP_ATTITUDE,
    MSP_NAV_STATUS,
    MSP_RAW_GPS,
    MSP_STATUS,
    MSP_STATUS_EX,
    read_i16_le,
    read_i32_le,
    read_u16_le,
)
from app.core.telemetry_state import TelemetryState


class MspParser(QObject):
    telemetry_updated = Signal(object)
    packet_received = Signal(int, bytes)
    message = Signal(str, str)
    home_set = Signal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self._buffer: list[int] = []
        self.state = TelemetryState()

    def reset(self) -> None:
        self._buffer.clear()
        self.state = TelemetryState()
        self.telemetry_updated.emit(self.state)

    def feed(self, data: bytes) -> None:
        for byte in data:
            self._buffer.append(byte)
            if len(self._buffer) > 4096:
                self._buffer.clear()
                self.message.emit("MSP parser buffer overflow; buffer reset", "warn")
                return
            self._consume()

    def _consume(self) -> None:
        while len(self._buffer) >= 6:
            if self._buffer[0:2] != [ord("$"), ord("M")] or self._buffer[2] not in [ord(">"), ord("!")]:
                self._buffer.pop(0)
                continue

            direction = self._buffer[2]
            size = self._buffer[3]
            command = self._buffer[4]
            packet_len = size + 6

            if len(self._buffer) < packet_len:
                return

            payload = bytes(self._buffer[5 : 5 + size])
            checksum = self._buffer[5 + size]
            calc = size ^ command

            for payload_byte in payload:
                calc ^= payload_byte

            del self._buffer[:packet_len]

            if calc != checksum:
                self.message.emit("MSP checksum mismatch", "warn")
                continue

            if direction == ord("!"):
                self.message.emit(f"MSP command {command} rejected or unsupported by FC", "error")
                continue

            self.packet_received.emit(command, payload)
            self._handle_response(command, payload)

    def _handle_response(self, command: int, payload: bytes) -> None:
        if command == MSP_API_VERSION and len(payload) >= 3:
            self.state.api_version = f"{payload[0]}.{payload[1]}.{payload[2]}"
            self.message.emit(f"INAV API {self.state.api_version}", "info")

        elif command == MSP_ATTITUDE and len(payload) >= 6:
            yaw = read_i16_le(payload, 4)
            self.state.heading_deg = yaw + 360 if yaw < 0 else yaw

        elif command == MSP_ANALOG and len(payload) >= 5:
            self.state.voltage = payload[0] / 10.0
            raw_rssi = read_u16_le(payload, 3)
            self.state.link_quality = min(100, round((raw_rssi / 1023) * 100))

        elif command == MSP_NAV_STATUS and len(payload) >= 1:
            self.state.nav_mode = payload[0]
            self.state.update_flight_mode()

        elif command == MSP_STATUS_EX:
            # Latency is measured by the polling layer; this packet confirms the link is alive.
            pass

        elif command == MSP_RAW_GPS and len(payload) >= 18:
            self.state.gps_fix = payload[0]
            self.state.satellites = payload[1]
            self.state.lat = read_i32_le(payload, 2) / 1e7
            self.state.lon = read_i32_le(payload, 6) / 1e7
            self.state.altitude_m = read_i16_le(payload, 10) / 100.0
            self.state.speed_ms = read_i16_le(payload, 12) / 100.0
            self.state.hdop = read_u16_le(payload, 16) / 100.0

            if self.state.maybe_set_home():
                self.home_set.emit(self.state.home_lat, self.state.home_lon)

        elif command == MSP_STATUS and len(payload) >= 11:
            flags = (
                payload[6]
                | (payload[7] << 8)
                | (payload[8] << 16)
                | (payload[9] << 24)
            )
            self.state.armed = bool(flags & (1 << 0))
            self.state.angle_mode = bool(flags & (1 << 3))
            if not self.state.armed:
                self.state.home_set = False
            self.state.update_flight_mode()

        self.telemetry_updated.emit(self.state)
