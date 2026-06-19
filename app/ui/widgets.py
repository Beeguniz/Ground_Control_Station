from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatTile(QFrame):
    def __init__(self, label: str, value: str = "--") -> None:
        super().__init__()
        self.setMinimumWidth(82)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(1)

        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "statValue")

        self.name_label = QLabel(label)
        self.name_label.setProperty("class", "statLabel")

        layout.addWidget(self.value_label)
        layout.addWidget(self.name_label)

    def set_value(self, value: str, color: str | None = None) -> None:
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color};")
        else:
            self.value_label.setStyleSheet("")
