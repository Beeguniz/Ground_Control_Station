from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.map.tile_proxy import TileProxyServer
from app.ui.main_window import MainWindow
from app.ui.theme import APP_QSS


def main() -> int:
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("E32 Flight Guide")
    app.setStyleSheet(APP_QSS)

    tile_proxy = TileProxyServer(host="127.0.0.1", port=8787)
    tile_proxy.start()
    app.aboutToQuit.connect(tile_proxy.stop)

    window = MainWindow()
    window.resize(1280, 760)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
