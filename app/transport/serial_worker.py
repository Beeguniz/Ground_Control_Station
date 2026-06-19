from __future__ import annotations

import time

import serial
from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app.core.msp import (
    MSP_ANALOG,
    MSP_API_VERSION,
    MSP_ATTITUDE,
    MSP_NAV_STATUS,
    MSP_RAW_GPS,
    MSP_STATUS,
    MSP_STATUS_EX,
    build_msp,
)


class SerialWorker(QObject):
    connected = Signal()
    disconnected = Signal()
    data_received = Signal(bytes)
    message = Signal(str, str)
    latency_sample = Signal(float)
    bytes_received = Signal(int)
    bytes_sent = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._serial: serial.Serial | None = None
        self._read_timer = QTimer(self)
        self._read_timer.setInterval(20)
        self._read_timer.timeout.connect(self._read_available)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(800)
        self._poll_timer.timeout.connect(self._poll)

        self._poll_cycle = 0
        self._last_status_ex_time = 0.0

    @Slot(str, int)
    def connect_port(self, port: str, baudrate: int) -> None:
        if self._serial and self._serial.is_open:
            return

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0,
                write_timeout=0.5,
                rtscts=False,
                dsrdtr=False,
            )
            self._serial.dtr = False
            self._serial.rts = False
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except serial.SerialException as exc:
            self.message.emit(f"Cannot open {port}: {exc}", "error")
            return

        self._poll_cycle = 0
        self._last_status_ex_time = 0.0
        self.message.emit(f"Serial open: {port} @ {baudrate}", "info")
        self.connected.emit()
        self._read_timer.start()
        self._poll_timer.start()
        self.send_handshake()
        QTimer.singleShot(250, self.send_handshake)
        QTimer.singleShot(750, self.send_handshake)

    @Slot()
    def disconnect_port(self) -> None:
        self._poll_timer.stop()
        self._read_timer.stop()

        if self._serial:
            try:
                self._serial.close()
            except serial.SerialException:
                pass

        self._serial = None
        self.disconnected.emit()
        self.message.emit("Serial disconnected", "warn")

    @Slot(bytes)
    def write(self, data: bytes) -> None:
        if not self._serial or not self._serial.is_open:
            return

        try:
            written = self._serial.write(data)
            self.bytes_sent.emit(written)
        except serial.SerialException as exc:
            self.message.emit(f"Serial write failed: {exc}", "error")
            self.disconnect_port()

    @Slot()
    def send_handshake(self) -> None:
        self.write(build_msp(MSP_API_VERSION))

    def _read_available(self) -> None:
        if not self._serial or not self._serial.is_open:
            return

        try:
            waiting = self._serial.in_waiting
            if waiting:
                data = self._serial.read(waiting)
                self.bytes_received.emit(len(data))
                self.data_received.emit(data)
        except serial.SerialException as exc:
            self.message.emit(f"Serial read failed: {exc}", "error")
            self.disconnect_port()

    def _poll(self) -> None:
        if not self._serial or not self._serial.is_open:
            return

        cycle = self._poll_cycle % 6

        if cycle == 0:
            self.write(build_msp(MSP_NAV_STATUS))
            self.write(build_msp(MSP_ATTITUDE))
        elif cycle == 1:
            self.write(build_msp(MSP_ANALOG))
        elif cycle == 2:
            self.write(build_msp(MSP_RAW_GPS))
        elif cycle == 3:
            self.write(build_msp(MSP_STATUS))
        elif cycle == 4:
            self.write(build_msp(MSP_API_VERSION))
        elif cycle == 5:
            self._last_status_ex_time = time.perf_counter()
            self.write(build_msp(MSP_STATUS_EX))
            self.latency_sample.emit(0.0)

        self._poll_cycle += 1

    @Slot()
    def mark_status_ex_response(self) -> None:
        if self._last_status_ex_time:
            self.latency_sample.emit((time.perf_counter() - self._last_status_ex_time) * 1000.0)
