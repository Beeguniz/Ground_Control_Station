from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional


MAP_SOURCES = [
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
]

SAT_SOURCES = [
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
]


def _content_type(payload: bytes) -> str:
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "application/octet-stream"


def _fetch_tile(layer: str, z: int, x: int, y: int) -> tuple[bytes, str]:
    sources = SAT_SOURCES if layer == "sat" else MAP_SOURCES
    headers = {
        "User-Agent": "E32FlightGuide/1.0 (+local-tile-proxy)",
        "Referer": "https://localhost/flight-guide",
    }

    for template in sources:
        url = template.format(z=z, x=x, y=y)
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = response.read()
                ctype = response.headers.get("Content-Type", "").split(";")[0].strip()
                return payload, ctype or _content_type(payload)
        except (TimeoutError, OSError, urllib.error.URLError):
            continue

    raise RuntimeError("upstream tile unavailable")


class _TileHandler(BaseHTTPRequestHandler):
    server_version = "E32TileProxy/1.0"

    def do_GET(self) -> None:
        self._serve_tile(send_body=True)

    def do_HEAD(self) -> None:
        self._serve_tile(send_body=False)

    def _serve_tile(self, send_body: bool) -> None:
        parts = self.path.split("?", 1)[0].strip("/").split("/")
        if len(parts) != 5 or parts[0] != "tiles":
            self._send_text(404, b"not found")
            return

        layer = parts[1]
        if layer not in {"map", "sat"}:
            self._send_text(404, b"unknown layer")
            return

        try:
            z = int(parts[2])
            x = int(parts[3])
            y = int(parts[4].split(".", 1)[0])
        except ValueError:
            self._send_text(400, b"bad tile path")
            return

        try:
            payload, ctype = _fetch_tile(layer, z, x, y)
        except RuntimeError:
            self._send_text(502, b"upstream unavailable")
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if send_body:
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return

    def _send_text(self, code: int, payload: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def log_message(self, _format: str, *_args) -> None:
        return


class TileProxyServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8787) -> None:
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._server:
            return
        self._server = ThreadingHTTPServer((self.host, self.port), _TileHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
