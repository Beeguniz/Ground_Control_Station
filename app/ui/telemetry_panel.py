from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout

from app.core.telemetry_state import TelemetryState
from app.ui.widgets import StatTile


class TelemetryPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TelemetryBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.sat = StatTile("SAT", "0")
        self.fix = StatTile("GPS", "NO FIX")
        self.batt = StatTile("BATT", "0.0V")
        self.lq = StatTile("LQ", "0%")
        self.armed = StatTile("ARM", "DISARMED")
        self.mode = StatTile("MODE", "MANUAL")
        self.link = StatTile("LINK", "--")
        self.speed = StatTile("SPEED", "0.0 m/s")
        self.alt = StatTile("ALT", "0.0 m")

        for tile in [
            self.sat,
            self.fix,
            self.batt,
            self.lq,
            self.armed,
            self.mode,
            self.link,
            self.speed,
            self.alt,
        ]:
            layout.addWidget(tile)

        layout.addStretch(1)

    def update_from_state(self, state: TelemetryState) -> None:
        self.sat.set_value(str(state.satellites))

        fix_text = "3D FIX" if state.gps_fix >= 2 else "2D FIX" if state.gps_fix == 1 else "NO FIX"
        fix_color = "#22c55e" if state.gps_fix >= 2 else "#f59e0b" if state.gps_fix == 1 else "#ef4444"
        self.fix.set_value(fix_text, fix_color)

        self.batt.set_value(f"{state.voltage:.1f}V")
        self.lq.set_value(f"{state.link_quality}%")
        self.armed.set_value("ARMED" if state.armed else "DISARMED", "#ef4444" if state.armed else "#22c55e")
        self.mode.set_value(state.flight_mode)
        self.speed.set_value(f"{state.speed_ms:.1f} m/s")
        self.alt.set_value(f"{state.altitude_m:.1f} m")

    def set_latency(self, latency_ms: float) -> None:
        if latency_ms <= 0:
            return
        color = "#22c55e" if latency_ms < 180 else "#f59e0b" if latency_ms < 350 else "#ef4444"
        self.link.set_value(f"{latency_ms:.0f} ms", color)
