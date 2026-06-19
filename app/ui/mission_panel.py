from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.mission.mission_model import MissionAction, MissionItem, renumber
from app.mission.mission_validator import validate_mission


class MissionPanel(QFrame):
    save_requested = Signal()
    load_requested = Signal()
    fetch_requested = Signal()
    upload_requested = Signal()
    eeprom_requested = Signal()
    clear_requested = Signal()
    mission_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setMinimumWidth(310)
        self.setMaximumWidth(390)
        self.setMinimumHeight(0)
        self.mission: list[MissionItem] = []
        self._loading_editor = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Mission")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")

        toolbar_wrap = QWidget()
        toolbar = QGridLayout(toolbar_wrap)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setHorizontalSpacing(6)
        toolbar.setVerticalSpacing(6)
        self.save_button = QPushButton("Save")
        self.load_button = QPushButton("Load")
        self.fetch_button = QPushButton("Fetch")
        self.upload_button = QPushButton("Upload")
        self.eeprom_button = QPushButton("EEPROM")
        self.clear_button = QPushButton("Clear")
        self.delete_wp_button = QPushButton("Delete WP")

        buttons = [
            self.save_button,
            self.load_button,
            self.fetch_button,
            self.upload_button,
            self.eeprom_button,
            self.clear_button,
            self.delete_wp_button,
        ]
        for idx, button in enumerate(buttons):
            row = 0 if idx < 4 else 1
            col = idx if idx < 4 else idx - 4
            button.setMinimumHeight(30)
            toolbar.addWidget(button, row, col)

        for col in range(4):
            toolbar.setColumnStretch(col, 1)

        self.summary = QLabel("Distance: -- | ETA: -- | WP: 0")
        self.summary.setProperty("class", "subtle")

        self.list_widget = QListWidget()
        self.list_widget.addItem("Click on map to add waypoints")
        self.list_widget.setMinimumHeight(130)

        editor_container = QWidget()
        editor_container_layout = QVBoxLayout(editor_container)
        editor_container_layout.setContentsMargins(0, 0, 0, 0)
        editor_container_layout.setSpacing(8)

        editor = QGroupBox("Waypoint Editor")
        editor_layout = QFormLayout(editor)
        editor_layout.setContentsMargins(8, 10, 8, 8)
        editor_layout.setSpacing(6)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["WAYPOINT", "PH_TIME", "POI", "LAND"])

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90, 90)
        self.lat_spin.setDecimals(7)
        self.lat_spin.setSingleStep(0.0001)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180, 180)
        self.lon_spin.setDecimals(7)
        self.lon_spin.setSingleStep(0.0001)

        self.alt_spin = QDoubleSpinBox()
        self.alt_spin.setRange(0, 10000)
        self.alt_spin.setDecimals(1)
        self.alt_spin.setSuffix(" m")

        self.p1_spin = QSpinBox()
        self.p1_spin.setRange(-32768, 32767)
        self.p2_spin = QSpinBox()
        self.p2_spin.setRange(-32768, 32767)
        self.p3_spin = QSpinBox()
        self.p3_spin.setRange(-32768, 32767)

        editor_layout.addRow("Type", self.type_combo)
        editor_layout.addRow("Lat", self.lat_spin)
        editor_layout.addRow("Lon", self.lon_spin)
        editor_layout.addRow("Alt", self.alt_spin)
        editor_layout.addRow("P1", self.p1_spin)
        editor_layout.addRow("P2", self.p2_spin)
        editor_layout.addRow("P3", self.p3_spin)

        action_box = QGroupBox("Command Action")
        action_layout = QFormLayout(action_box)
        action_layout.setContentsMargins(8, 10, 8, 8)
        action_layout.setSpacing(6)

        self.action_combo = QComboBox()
        self.action_combo.addItems(["SET_HEAD", "JUMP", "RTH"])
        self.action_p1_spin = QSpinBox()
        self.action_p1_spin.setRange(-32768, 32767)
        self.action_p2_spin = QSpinBox()
        self.action_p2_spin.setRange(-32768, 32767)

        action_buttons = QHBoxLayout()
        self.add_action_button = QPushButton("Add/Update")
        self.delete_action_button = QPushButton("Delete")
        action_buttons.addWidget(self.add_action_button)
        action_buttons.addWidget(self.delete_action_button)

        action_layout.addRow("Action", self.action_combo)
        action_layout.addRow("P1", self.action_p1_spin)
        action_layout.addRow("P2", self.action_p2_spin)
        action_layout.addRow(action_buttons)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("color: #f59e0b;")

        editor_container_layout.addWidget(editor)
        editor_container_layout.addWidget(action_box)
        editor_container_layout.addWidget(self.validation_label)
        editor_container_layout.addStretch(1)

        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setFrameShape(QFrame.NoFrame)
        editor_scroll.setMinimumHeight(220)
        editor_scroll.setWidget(editor_container)

        layout.addWidget(title)
        layout.addWidget(toolbar_wrap)
        layout.addWidget(self.summary)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(editor_scroll, 1)

        self.save_button.clicked.connect(self.save_requested)
        self.load_button.clicked.connect(self.load_requested)
        self.fetch_button.clicked.connect(self.fetch_requested)
        self.upload_button.clicked.connect(self.upload_requested)
        self.eeprom_button.clicked.connect(self.eeprom_requested)
        self.clear_button.clicked.connect(self.clear_requested)
        self.delete_wp_button.clicked.connect(self.delete_selected_waypoint)
        self.list_widget.currentRowChanged.connect(self._load_selected_item)

        self.type_combo.currentTextChanged.connect(self._apply_editor)
        self.lat_spin.valueChanged.connect(self._apply_editor)
        self.lon_spin.valueChanged.connect(self._apply_editor)
        self.alt_spin.valueChanged.connect(self._apply_editor)
        self.p1_spin.valueChanged.connect(self._apply_editor)
        self.p2_spin.valueChanged.connect(self._apply_editor)
        self.p3_spin.valueChanged.connect(self._apply_editor)
        self.add_action_button.clicked.connect(self._add_or_update_action)
        self.delete_action_button.clicked.connect(self._delete_action)
        self._set_editor_enabled(False)
        self.delete_wp_button.setEnabled(False)

    def add_waypoint(self, lat: float, lon: float) -> None:
        self.mission.append(
            MissionItem(
                id=len(self.mission) + 1,
                lat=lat,
                lon=lon,
                alt=50.0,
                type="WAYPOINT",
                p1=500,
            )
        )
        self.render()
        self.list_widget.setCurrentRow(len(self.mission) - 1)
        self.mission_changed.emit()

    def set_mission(self, mission: list[MissionItem]) -> None:
        self.mission = list(mission)
        renumber(self.mission)
        self.render()
        self.list_widget.setCurrentRow(0 if self.mission else -1)
        self.mission_changed.emit()

    def delete_selected_waypoint(self) -> None:
        index = self._selected_index()
        if index < 0:
            return

        del self.mission[index]
        renumber(self.mission)
        self.render()

        if self.mission:
            self.list_widget.setCurrentRow(min(index, len(self.mission) - 1))
        else:
            self.list_widget.setCurrentRow(-1)

        self.mission_changed.emit()

    def clear_mission(self) -> None:
        self.mission.clear()
        self.render()
        self.mission_changed.emit()

    def render(self) -> None:
        self.list_widget.clear()

        if not self.mission:
            self.list_widget.addItem("Click on map to add waypoints")
            self.summary.setText("Distance: -- | ETA: -- | WP: 0")
            self.validation_label.setText("")
            self._set_editor_enabled(False)
            self.delete_wp_button.setEnabled(False)
            return

        for item in self.mission:
            action_text = ""
            if item.actions:
                action_text = " | " + ", ".join(f"{action.type}({action.p1},{action.p2})" for action in item.actions)
            self.list_widget.addItem(
                f"#{item.id} {item.type} | alt={item.alt:.0f}m | p1={item.p1} | "
                f"{item.lat:.6f}, {item.lon:.6f}{action_text}"
            )

        self.summary.setText(f"Distance: -- | ETA: -- | WP: {len(self.mission)}")
        self._render_validation()
        self.delete_wp_button.setEnabled(True)

    def _selected_index(self) -> int:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.mission):
            return -1
        return row

    def _load_selected_item(self, row: int) -> None:
        if row < 0 or row >= len(self.mission):
            self._set_editor_enabled(False)
            return

        item = self.mission[row]
        self._loading_editor = True
        self._set_editor_enabled(True)
        self.type_combo.setCurrentText(item.type)
        self.lat_spin.setValue(item.lat)
        self.lon_spin.setValue(item.lon)
        self.alt_spin.setValue(item.alt)
        self.p1_spin.setValue(item.p1)
        self.p2_spin.setValue(item.p2)
        self.p3_spin.setValue(item.p3)

        if item.actions:
            action = item.actions[0]
            self.action_combo.setCurrentText(action.type)
            self.action_p1_spin.setValue(action.p1)
            self.action_p2_spin.setValue(action.p2)
        else:
            self.action_combo.setCurrentText("SET_HEAD")
            self.action_p1_spin.setValue(0)
            self.action_p2_spin.setValue(0)

        self._loading_editor = False

    def _apply_editor(self) -> None:
        if self._loading_editor:
            return

        index = self._selected_index()
        if index < 0:
            return

        item = self.mission[index]
        item.type = self.type_combo.currentText()  # type: ignore[assignment]
        item.lat = self.lat_spin.value()
        item.lon = self.lon_spin.value()
        item.alt = self.alt_spin.value()
        item.p1 = self.p1_spin.value()
        item.p2 = self.p2_spin.value()
        item.p3 = self.p3_spin.value()
        self._rerender_keep_selection(index)
        self.mission_changed.emit()

    def _add_or_update_action(self) -> None:
        index = self._selected_index()
        if index < 0:
            return

        action = MissionAction(
            type=self.action_combo.currentText(),  # type: ignore[arg-type]
            p1=self.action_p1_spin.value(),
            p2=self.action_p2_spin.value(),
            p3=0,
        )

        item = self.mission[index]
        if item.actions:
            item.actions[0] = action
        else:
            item.actions.append(action)

        self._rerender_keep_selection(index)
        self.mission_changed.emit()

    def _delete_action(self) -> None:
        index = self._selected_index()
        if index < 0:
            return

        self.mission[index].actions.clear()
        self._load_selected_item(index)
        self._rerender_keep_selection(index)
        self.mission_changed.emit()

    def _rerender_keep_selection(self, index: int) -> None:
        self._loading_editor = True
        self.render()
        self.list_widget.setCurrentRow(index)
        self._loading_editor = False
        self._load_selected_item(index)

    def _render_validation(self) -> None:
        results = validate_mission(self.mission)
        if not results:
            self.validation_label.setText("")
            return

        lines = []
        for result in results[:4]:
            prefix = f"WP{result.wp}: " if result.wp > 0 else ""
            lines.append(f"{result.level.upper()}: {prefix}{result.message}")

        if len(results) > 4:
            lines.append(f"... {len(results) - 4} more")

        self.validation_label.setText("\n".join(lines))

    def _set_editor_enabled(self, enabled: bool) -> None:
        for widget in [
            self.type_combo,
            self.lat_spin,
            self.lon_spin,
            self.alt_spin,
            self.p1_spin,
            self.p2_spin,
            self.p3_spin,
            self.action_combo,
            self.action_p1_spin,
            self.action_p2_spin,
            self.add_action_button,
            self.delete_action_button,
        ]:
            widget.setEnabled(enabled)
