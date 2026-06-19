from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.core.telemetry_state import TelemetryState


class MapBridge(QObject):
    def __init__(self, on_click) -> None:
        super().__init__()
        self._on_click = on_click

    @Slot(float, float)
    def mapClicked(self, lat: float, lon: float) -> None:
        self._on_click(lat, lon)


class MapPage(QWebEnginePage):
    js_message = Signal(str)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):  # type: ignore[override]
        self.js_message.emit(f"JS[{level}] {sourceID}:{lineNumber} {message}")
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class MapView(QWebEngineView):
    map_message = Signal(str)

    def __init__(self, on_map_click) -> None:
        super().__init__()
        self._loaded = False
        self._pending_scripts: list[str] = []
        self._page = MapPage(self)
        self.setPage(self._page)
        self._enable_local_map_access()
        self._page.js_message.connect(self.map_message.emit)

        self._channel = QWebChannel(self.page())
        self._bridge = MapBridge(on_map_click)
        self._channel.registerObject("qtBridge", self._bridge)
        self.page().setWebChannel(self._channel)
        self.loadFinished.connect(self._on_load_finished)

        html_path = Path(__file__).with_name("map.html").resolve()
        self.load(QUrl.fromLocalFile(str(html_path)))

    def run_js(self, script: str) -> None:
        if not self._loaded:
            self._pending_scripts.append(script)
            return
        self.page().runJavaScript(script)

    def set_mission(self, mission) -> None:
        payload = [{"lat": float(item.lat), "lon": float(item.lon)} for item in mission]
        self.run_js(f"window.setMission({json.dumps(payload)});")

    def update_telemetry(self, state: TelemetryState) -> None:
        if state.gps_fix >= 2 and state.lat and state.lon:
            self.run_js(f"window.setDrone({state.lat:.8f}, {state.lon:.8f}, {state.heading_deg:.2f});")
            if state.armed:
                self.run_js(f"window.addTrailPoint({state.lat:.8f}, {state.lon:.8f});")

    def set_home(self, lat: float, lon: float) -> None:
        self.run_js(f"window.setHome({lat:.8f}, {lon:.8f});")

    def _on_load_finished(self, ok: bool) -> None:
        self._loaded = True
        if not ok:
            self.map_message.emit("Map HTML failed to load")
            return
        for script in self._pending_scripts:
            self.page().runJavaScript(script)
        self._pending_scripts.clear()

    def _enable_local_map_access(self) -> None:
        settings = self.page().settings()

        for attr_name in ("LocalContentCanAccessRemoteUrls", "LocalContentCanAccessFileUrls"):
            try:
                attr = getattr(QWebEngineSettings.WebAttribute, attr_name)
            except AttributeError:
                attr = getattr(QWebEngineSettings, attr_name)
            settings.setAttribute(attr, True)
