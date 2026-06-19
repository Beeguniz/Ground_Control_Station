APP_QSS = """
QMainWindow {
    background: #101418;
    color: #e5e7eb;
}

QWidget {
    font-family: Segoe UI, Arial;
    font-size: 12px;
    color: #e5e7eb;
}

QFrame#TopBar,
QFrame#Sidebar,
QFrame#TelemetryBar,
QFrame#LogPanel {
    background: #171c22;
    border: 1px solid #2a313a;
}

QLabel#Brand {
    font-size: 17px;
    font-weight: 700;
}

QLabel#Subtle,
QLabel.subtle {
    color: #9ca3af;
}

QLabel.statValue {
    font-size: 16px;
    font-weight: 700;
}

QLabel.statLabel {
    color: #9ca3af;
    font-size: 10px;
}

QPushButton {
    background: #25303a;
    border: 1px solid #3a4654;
    border-radius: 6px;
    padding: 6px 10px;
}

QPushButton:hover {
    background: #2f3b48;
}

QPushButton#ConnectButton {
    background: #2563eb;
    border-color: #3b82f6;
    font-weight: 700;
}

QPushButton#DisconnectButton {
    background: #991b1b;
    border-color: #dc2626;
    font-weight: 700;
}

QComboBox {
    background: #111820;
    border: 1px solid #344152;
    border-radius: 6px;
    padding: 5px 8px;
    color: #f8fafc;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QComboBox:hover {
    border-color: #4b5b6d;
    background: #141d27;
}

QComboBox:focus {
    border-color: #38bdf8;
}

QComboBox:disabled {
    background: #111820;
    border-color: #26313d;
    color: #6b7280;
}

QComboBox::drop-down {
    width: 24px;
    border: 0;
    border-left: 1px solid #26313d;
    background: #0d141c;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}

QComboBox QAbstractItemView {
    background: #111820;
    border: 1px solid #344152;
    color: #e5e7eb;
    outline: 0;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 6px 10px;
}

QComboBox QAbstractItemView::item:hover {
    background: #1f2a36;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:selected {
    background: #2563eb;
    color: #ffffff;
}

QSpinBox,
QDoubleSpinBox {
    background: #111820;
    border: 1px solid #344152;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    min-height: 24px;
}

QSpinBox:hover,
QDoubleSpinBox:hover {
    border-color: #4b5b6d;
    background: #141d27;
}

QSpinBox:focus,
QDoubleSpinBox:focus {
    border-color: #38bdf8;
}

QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background: #101821;
    border-color: #26313d;
    color: #8ea0b4;
}

QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {
    width: 18px;
    border: 0;
    background: #0d141c;
}

QGroupBox {
    background: #121922;
    border: 1px solid #2f3c4a;
    border-radius: 7px;
    margin-top: 12px;
    padding-top: 12px;
    color: #d1d5db;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #b9c4d0;
    background: #171c22;
}

QGroupBox QLabel {
    color: #aeb9c6;
}

QGroupBox QComboBox {
    min-height: 24px;
    padding: 6px 10px;
}

QScrollArea {
    background: transparent;
}

QScrollBar:vertical {
    background: #101821;
    width: 9px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #475569;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #64748b;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    border: 0;
}

QPlainTextEdit {
    background: #0b0f14;
    border: 1px solid #2a313a;
    color: #d1d5db;
}

QListWidget {
    background: #111820;
    border: 1px solid #2a313a;
}
"""
