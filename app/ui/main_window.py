from __future__ import annotations

import socket
import threading
import urllib.request

from serial.tools import list_ports

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.msp import MSP_STATUS_EX
from app.core.msp_parser import MspParser
from app.map.map_view import MapView
from app.mission.mission_file import build_mission_xml, parse_mission_xml
from app.mission.mission_msp import MissionMsp
from app.mission.mission_validator import validate_mission
from app.transport.serial_worker import SerialWorker
from app.ui.log_panel import LogPanel
from app.ui.mission_panel import MissionPanel
from app.ui.telemetry_panel import TelemetryPanel


class MainWindow(QMainWindow):
    connect_serial_requested = Signal(str, int)
    disconnect_serial_requested = Signal()
    status_ex_received = Signal()
    handshake_requested = Signal()
    send_bytes_requested = Signal(bytes)
    map_diag_message = Signal(str, str)
    map_diag_done = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("E32 Flight Guide - Windows GCS")

        self.parser = MspParser()
        self.mission_msp = MissionMsp()
        self.serial_thread = QThread(self)
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.start()

        self._connected = False
        self._msp_active = False
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._packet_count = 0
        self._handshake_timer = QTimer(self)
        self._handshake_timer.setSingleShot(True)
        self._handshake_timer.setInterval(3500)
        self._handshake_timer.timeout.connect(self._on_handshake_timeout)

        self._build_ui()
        self._connect_signals()
        self.refresh_ports()

    def closeEvent(self, event) -> None:
        self.disconnect_serial_requested.emit()
        self.serial_thread.quit()
        self.serial_thread.wait(1200)
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        topbar = QFrame()
        topbar.setObjectName("TopBar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(10, 7, 10, 7)

        brand = QLabel("E32 Flight Guide")
        brand.setObjectName("Brand")
        subtitle = QLabel("INAV GCS | LoRa E32 Serial")
        subtitle.setProperty("class", "subtle")

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("57600")

        self.refresh_button = QPushButton("Refresh")
        self.check_map_button = QPushButton("Check Map")
        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("ConnectButton")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: 700;")
        self.io_label = QLabel("RX 0 | TX 0 | PKT 0")
        self.io_label.setStyleSheet("color: #9ca3af;")

        top_layout.addWidget(brand)
        top_layout.addWidget(subtitle)
        top_layout.addStretch(1)
        top_layout.addWidget(QLabel("COM"))
        top_layout.addWidget(self.port_combo)
        top_layout.addWidget(QLabel("Baud"))
        top_layout.addWidget(self.baud_combo)
        top_layout.addWidget(self.refresh_button)
        top_layout.addWidget(self.check_map_button)
        top_layout.addWidget(self.connect_button)
        top_layout.addWidget(self.status_label)
        top_layout.addWidget(self.io_label)

        self.telemetry_panel = TelemetryPanel()
        self.mission_panel = MissionPanel()
        self.map_view = MapView(self._on_map_click)
        self.log_panel = LogPanel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.mission_panel)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 1000])

        main_layout.addWidget(topbar)
        main_layout.addWidget(self.telemetry_panel)
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(self.log_panel)

        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.check_map_button.clicked.connect(self.run_map_diagnostics)
        self.connect_button.clicked.connect(self.toggle_connection)

        self.serial_worker.connected.connect(self._on_connected)
        self.serial_worker.disconnected.connect(self._on_disconnected)
        self.serial_worker.data_received.connect(self.parser.feed)
        self.serial_worker.message.connect(self.log_panel.add_message)
        self.serial_worker.latency_sample.connect(self.telemetry_panel.set_latency)
        self.serial_worker.bytes_received.connect(self._on_bytes_received)
        self.serial_worker.bytes_sent.connect(self._on_bytes_sent)
        self.connect_serial_requested.connect(self.serial_worker.connect_port)
        self.disconnect_serial_requested.connect(self.serial_worker.disconnect_port)
        self.status_ex_received.connect(self.serial_worker.mark_status_ex_response)
        self.handshake_requested.connect(self.serial_worker.send_handshake)
        self.send_bytes_requested.connect(self.serial_worker.write)

        self.parser.telemetry_updated.connect(self.telemetry_panel.update_from_state)
        self.parser.telemetry_updated.connect(self.map_view.update_telemetry)
        self.parser.message.connect(self.log_panel.add_message)
        self.parser.home_set.connect(self.map_view.set_home)
        self.parser.packet_received.connect(self._on_packet_received)
        self.parser.packet_received.connect(self.mission_msp.handle_packet)
        self.map_view.map_message.connect(lambda m: self.log_panel.add_message(m, "warn"))
        self.map_diag_message.connect(self.log_panel.add_message)
        self.map_diag_done.connect(lambda: self.check_map_button.setEnabled(True))

        self.mission_msp.send_bytes.connect(self.send_bytes_requested)
        self.mission_msp.message.connect(self.log_panel.add_message)
        self.mission_msp.mission_loaded.connect(self._on_mission_loaded)

        self.mission_panel.save_requested.connect(self._save_mission_file)
        self.mission_panel.load_requested.connect(self._load_mission_file)
        self.mission_panel.fetch_requested.connect(self._fetch_mission_from_fc)
        self.mission_panel.upload_requested.connect(self._upload_mission_to_fc)
        self.mission_panel.eeprom_requested.connect(self._save_eeprom)
        self.mission_panel.clear_requested.connect(self._clear_mission)
        self.mission_panel.mission_changed.connect(self._on_mission_changed)

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = [port.device for port in list_ports.comports()]
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)
        if not ports:
            self.log_panel.add_message("No COM ports found", "warn")

    def toggle_connection(self) -> None:
        if self._connected:
            self.disconnect_serial_requested.emit()
            return

        port = self.port_combo.currentText()
        if not port:
            self.log_panel.add_message("Select a COM port first", "warn")
            return

        baudrate = int(self.baud_combo.currentText())
        self.connect_serial_requested.emit(port, baudrate)

    def _on_connected(self) -> None:
        self._connected = True
        self._msp_active = False
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._packet_count = 0
        self.parser.reset()
        self._update_io_label()
        self.connect_button.setText("Disconnect")
        self.connect_button.setObjectName("DisconnectButton")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.status_label.setText("Waiting MSP")
        self.status_label.setStyleSheet("color: #f59e0b; font-weight: 700;")
        self.log_panel.add_message("Serial opened. Waiting for MSP API_VERSION response from FC.", "info")
        self._handshake_timer.start()

    def _on_disconnected(self) -> None:
        self._connected = False
        self._msp_active = False
        self._handshake_timer.stop()
        self.connect_button.setText("Connect")
        self.connect_button.setObjectName("ConnectButton")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: 700;")

    def _on_packet_received(self, command: int, _payload: bytes) -> None:
        first_packet = not self._msp_active
        self._msp_active = True
        self._packet_count += 1
        self._handshake_timer.stop()
        self._update_io_label()

        if command == MSP_STATUS_EX:
            self.status_ex_received.emit()
        self.status_label.setText("MSP active")
        self.status_label.setStyleSheet("color: #22c55e; font-weight: 700;")
        if first_packet:
            self.log_panel.add_message("MSP response received. FC and GCS are communicating.", "info")

    def _on_map_click(self, lat: float, lon: float) -> None:
        self.mission_panel.add_waypoint(lat, lon)
        self.log_panel.add_message(f"Waypoint added: {lat:.6f}, {lon:.6f}", "info")

    def _on_bytes_received(self, count: int) -> None:
        self._rx_bytes += count
        self._update_io_label()

    def _on_bytes_sent(self, count: int) -> None:
        self._tx_bytes += count
        self._update_io_label()

    def _update_io_label(self) -> None:
        self.io_label.setText(f"RX {self._rx_bytes} | TX {self._tx_bytes} | PKT {self._packet_count}")

    def _on_handshake_timeout(self) -> None:
        if not self._connected or self._msp_active:
            return

        self.status_label.setText("No MSP")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: 700;")
        self.log_panel.add_message(
            "Serial is open but no MSP response arrived. Check baud rate, FC UART MSP setting, TX/RX wiring, and E32 pairing.",
            "error",
        )
        self.handshake_requested.emit()
        self._handshake_timer.start()

    def _save_mission_file(self) -> None:
        if not self.mission_panel.mission:
            self.log_panel.add_message("No mission to save", "warn")
            return

        validation = validate_mission(self.mission_panel.mission)
        for item in validation:
            prefix = f"WP{item.wp}: " if item.wp > 0 else ""
            self.log_panel.add_message(prefix + item.message, item.level)

        path, _ = QFileDialog.getSaveFileName(self, "Save mission", "mission.mission", "Mission (*.mission)")
        if not path:
            return

        with open(path, "w", encoding="utf-8") as file:
            file.write(build_mission_xml(self.mission_panel.mission))

        self.log_panel.add_message(f"Mission saved: {path}", "info")

    def _load_mission_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load mission", "", "Mission (*.mission)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                mission = parse_mission_xml(file.read())
        except Exception as exc:
            self.log_panel.add_message(f"Failed to load mission: {exc}", "error")
            return

        self.mission_panel.set_mission(mission)
        self.log_panel.add_message(f"Mission loaded: {len(mission)} waypoint(s)", "info")

    def _fetch_mission_from_fc(self) -> None:
        if not self._msp_active:
            self.log_panel.add_message("Connect to FC before fetching mission", "warn")
            return
        self.mission_msp.fetch_from_fc()

    def _upload_mission_to_fc(self) -> None:
        if not self._msp_active:
            self.log_panel.add_message("Connect to FC before uploading mission", "warn")
            return
        self.mission_msp.upload_to_fc(self.mission_panel.mission)

    def _save_eeprom(self) -> None:
        if not self._msp_active:
            self.log_panel.add_message("Connect to FC before writing EEPROM", "warn")
            return
        self.mission_msp.save_eeprom()

    def _clear_mission(self) -> None:
        self.mission_panel.clear_mission()
        self.log_panel.add_message("Mission cleared in UI", "warn")

    def _on_mission_loaded(self, mission: object) -> None:
        mission_list = list(mission)
        self.mission_panel.set_mission(mission_list)

    def _on_mission_changed(self) -> None:
        self.map_view.set_mission(self.mission_panel.mission)

    def run_map_diagnostics(self) -> None:
        self.check_map_button.setEnabled(False)
        self.map_diag_message.emit("Running map diagnostics...", "info")

        def worker() -> None:
            checks = [
                ("Local tile proxy map", self._check_http("http://127.0.0.1:8787/tiles/map/6/50/28.png")),
                ("Local tile proxy sat", self._check_http("http://127.0.0.1:8787/tiles/sat/6/50/28.png")),
                ("DNS tile.openstreetmap.org", self._check_dns("tile.openstreetmap.org")),
                ("HTTP OSM upstream", self._check_http("https://tile.openstreetmap.org/6/50/28.png")),
                ("HTTP Esri upstream", self._check_http("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/6/28/50")),
            ]

            for name, result in checks:
                level = "info" if result.startswith("OK") else "error"
                self.map_diag_message.emit(f"{name}: {result}", level)

            self.map_diag_message.emit("Map diagnostics finished.", "info")
            self.map_diag_done.emit()

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _check_dns(host: str) -> str:
        try:
            ip = socket.gethostbyname(host)
            return f"OK ({ip})"
        except Exception as exc:
            return f"FAIL ({exc})"

    @staticmethod
    def _check_http(url: str) -> str:
        try:
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "E32FlightGuide/1.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                return f"OK (HTTP {response.status})"
        except Exception as exc:
            return f"FAIL ({exc})"
