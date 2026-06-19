from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app.core.msp import build_msp
from app.mission.mission_model import (
    ACTION_TYPES,
    NAV_TYPES,
    MissionAction,
    MissionItem,
    decode_action_code,
    encode_action_type,
    flatten_mission,
    renumber,
)
from app.mission.mission_validator import validate_mission

MSP_WP_MISSION_LOAD = 18
MSP_WP_MISSION_SAVE = 19
MSP_WP_GETINFO = 20
MSP_WP = 118
MSP_WP_RESET = 204
MSP_SET_WP = 209
MSP_EEPROM_WRITE = 250


class MissionMsp(QObject):
    send_bytes = Signal(bytes)
    mission_loaded = Signal(object)
    message = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self._is_fetching = False
        self._expected_count = 0
        self._received_count = 0
        self._loaded_mission: list[MissionItem] = []
        self._upload_queue: list[bytes] = []
        self._verify_after_fetch = False
        self._verify_expected: list[MissionItem] = []
        self._fetch_generation = 0

    def fetch_from_fc(self, verify: bool = False) -> None:
        self._is_fetching = True
        self._fetch_generation += 1
        generation = self._fetch_generation
        self._verify_after_fetch = verify
        self._expected_count = 0
        self._received_count = 0
        self._loaded_mission = []

        self.message.emit("Verifying mission from FC..." if verify else "Fetching mission from FC...", "info")
        self._send(MSP_WP_RESET)
        QTimer.singleShot(80, lambda: self._send(MSP_WP_MISSION_LOAD, [0]))
        QTimer.singleShot(180, lambda: self._send(MSP_WP_GETINFO))
        QTimer.singleShot(5000, lambda: self._on_fetch_timeout(generation))

    def save_eeprom(self) -> None:
        self._send(MSP_EEPROM_WRITE)
        self.message.emit("EEPROM write command sent", "info")

    def upload_to_fc(self, mission: list[MissionItem]) -> None:
        if not mission:
            self.message.emit("No mission to upload", "warn")
            return

        validation = validate_mission(mission)
        blocking = [item for item in validation if item.level == "error"]
        if blocking:
            for item in blocking:
                prefix = f"WP{item.wp}: " if item.wp > 0 else ""
                self.message.emit(prefix + item.message, "error")
            self.message.emit("Mission upload blocked by validation errors", "error")
            return

        self._upload_queue.clear()
        flat = flatten_mission(mission)
        self._verify_expected = []
        self._upload_queue.append(build_msp(MSP_WP_MISSION_LOAD, [0]))
        self._upload_queue.append(build_msp(MSP_WP_RESET))

        for index, item in enumerate(flat):
            is_last = index == len(flat) - 1
            flag = 165 if is_last else 0
            item.id = index + 1
            item.flag = flag
            self._verify_expected.append(item)
            payload = bytes(
                [
                    index + 1,
                    encode_action_type(item.type),
                    *self._write_i32(round(item.lat * 1e7)),
                    *self._write_i32(round(item.lon * 1e7)),
                    *self._write_i32(round(item.alt * 100)),
                    *self._write_i16(item.p1),
                    *self._write_i16(item.p2),
                    *self._write_i16(item.p3),
                    flag,
                ]
            )
            self._upload_queue.append(build_msp(MSP_SET_WP, payload))

        self._upload_queue.append(build_msp(MSP_WP_MISSION_SAVE, [0]))
        self._upload_queue.append(build_msp(MSP_EEPROM_WRITE))
        self.message.emit(f"Uploading {len(flat)} mission item(s) to FC...", "info")
        self._drain_upload_queue()

    @Slot(int, bytes)
    def handle_packet(self, command: int, payload: bytes) -> None:
        if not self._is_fetching:
            return

        if command == MSP_WP_GETINFO:
            self._handle_wp_info(payload)
        elif command == MSP_WP:
            self._handle_wp(payload)

    def _handle_wp_info(self, payload: bytes) -> None:
        if len(payload) < 4:
            self.message.emit("Invalid MSP_WP_GETINFO payload", "warn")
            return

        ram_count = payload[0]
        eeprom_count = payload[3]
        count = ram_count if ram_count > 0 else eeprom_count

        if count == 0:
            self._is_fetching = False
            if self._verify_after_fetch:
                self._verify_after_fetch = False
                self.message.emit("Mission verify failed: FC reports no stored mission", "error")
            else:
                self.message.emit("No mission stored in FC", "warn")
                self.mission_loaded.emit([])
            return

        self._expected_count = count
        self.message.emit(f"FC reports {count} mission item(s)", "info")

        for index in range(1, count + 1):
            QTimer.singleShot(index * 35, lambda wp_index=index: self._send(MSP_WP, [wp_index]))

    def _handle_wp(self, payload: bytes) -> None:
        if len(payload) < 21:
            self.message.emit("Invalid MSP_WP payload", "warn")
            return

        wp_number = payload[0]
        action_code = payload[1]
        lat_raw = int.from_bytes(payload[2:6], "little", signed=True)
        lon_raw = int.from_bytes(payload[6:10], "little", signed=True)
        alt_raw = int.from_bytes(payload[10:14], "little", signed=True)
        p1 = int.from_bytes(payload[14:16], "little", signed=True)
        p2 = int.from_bytes(payload[16:18], "little", signed=True)
        p3 = int.from_bytes(payload[18:20], "little", signed=True)
        flag = payload[20]

        self._received_count += 1

        if wp_number == 0 and lat_raw == 0 and lon_raw == 0 and alt_raw == 0 and action_code == 0:
            self._finish_fetch_if_ready()
            return

        item_type = decode_action_code(action_code)

        if item_type in NAV_TYPES:
            self._loaded_mission.append(
                MissionItem(
                    id=len(self._loaded_mission) + 1,
                    lat=lat_raw / 1e7,
                    lon=lon_raw / 1e7,
                    alt=alt_raw / 100,
                    type=item_type,
                    p1=p1,
                    p2=p2,
                    p3=p3,
                    flag=flag,
                )
            )
        elif item_type in ACTION_TYPES and self._loaded_mission:
            self._loaded_mission[-1].actions.append(
                MissionAction(
                    type=item_type,  # type: ignore[arg-type]
                    p1=p1,
                    p2=p2,
                    p3=p3,
                )
            )

        self._finish_fetch_if_ready()

    def _finish_fetch_if_ready(self) -> None:
        if self._expected_count <= 0 or self._received_count < self._expected_count:
            return

        self._is_fetching = False
        renumber(self._loaded_mission)
        self.message.emit(f"Mission loaded from FC: {len(self._loaded_mission)} waypoint(s)", "info")
        if self._verify_after_fetch:
            self._verify_after_fetch = False
            self._verify_loaded_mission()
        self.mission_loaded.emit(self._loaded_mission)

    def _drain_upload_queue(self) -> None:
        if not self._upload_queue:
            self.message.emit("Mission upload complete. Starting FC verification...", "info")
            QTimer.singleShot(250, lambda: self.fetch_from_fc(verify=True))
            return

        packet = self._upload_queue.pop(0)
        self.send_bytes.emit(packet)
        QTimer.singleShot(55, self._drain_upload_queue)

    def _send(self, command: int, payload: list[int] | bytes = b"") -> None:
        self.send_bytes.emit(build_msp(command, payload))

    @staticmethod
    def _write_i32(value: int) -> list[int]:
        return list(value.to_bytes(4, "little", signed=True))

    @staticmethod
    def _write_i16(value: int) -> list[int]:
        return list(max(-32768, min(32767, int(value))).to_bytes(2, "little", signed=True))

    def _on_fetch_timeout(self, generation: int) -> None:
        if not self._is_fetching or generation != self._fetch_generation:
            return

        self._is_fetching = False
        if self._verify_after_fetch:
            self._verify_after_fetch = False
            self.message.emit("Mission verify failed: timeout waiting for FC mission response", "error")
        else:
            self.message.emit("Mission fetch timeout waiting for FC response", "error")

    def _verify_loaded_mission(self) -> None:
        actual = flatten_mission(self._loaded_mission)
        for index, item in enumerate(actual):
            item.id = index + 1
            item.flag = 165 if index == len(actual) - 1 else item.flag

        expected_raw = [self._raw_compare_tuple(item) for item in self._verify_expected]
        actual_raw = [self._raw_compare_tuple(item) for item in actual]

        if expected_raw == actual_raw:
            self.message.emit(f"MISSION VERIFIED: {len(actual)} item(s) match FC memory", "info")
            return

        self.message.emit(
            f"Mission verify failed: expected {len(expected_raw)} item(s), FC returned {len(actual_raw)} item(s)",
            "error",
        )

        for index, (expected, received) in enumerate(zip(expected_raw, actual_raw), start=1):
            if expected != received:
                self.message.emit(f"Mission verify mismatch at item {index}: expected {expected}, got {received}", "error")
                return

        if len(expected_raw) != len(actual_raw):
            self.message.emit("Mission verify mismatch: item count differs", "error")

    @staticmethod
    def _raw_compare_tuple(item: MissionItem) -> tuple[int, int, int, int, int, int, int, int, int]:
        return (
            item.id,
            encode_action_type(item.type),
            round(item.lat * 1e7),
            round(item.lon * 1e7),
            round(item.alt * 100),
            int(item.p1),
            int(item.p2),
            int(item.p3),
            int(item.flag),
        )
