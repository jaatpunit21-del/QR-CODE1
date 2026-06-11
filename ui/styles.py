# Stylesheet definitions for a premium, modern dark UI using PySide6 QSS.

DARK_STYLE_SHEET = """
/* Global Window Styling */
QMainWindow {
    background-color: #0f172a; /* Slate 900 */
    font-family: "Inter", "Segoe UI", Helvetica, Arial, sans-serif;
    color: #f8fafc; /* Slate 50 */
}

/* Sidebar Styling */
QFrame#SidebarFrame {
    background-color: #1e293b; /* Slate 800 */
    border-right: 1px solid #334155; /* Slate 700 */
}

QLabel#SidebarTitle {
    color: #3b82f6; /* Blue 500 */
    font-size: 18px;
    font-weight: bold;
    padding: 10px;
}

/* Sidebar Navigation Buttons */
QPushButton.NavButton {
    background-color: transparent;
    color: #94a3b8; /* Slate 400 */
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}

QPushButton.NavButton:hover {
    background-color: #334155; /* Slate 700 */
    color: #f8fafc;
}

QPushButton.NavButton:checked {
    background-color: #2563eb; /* Blue 600 */
    color: #ffffff;
    font-weight: bold;
}

/* Main Content Styling */
QFrame#ContentFrame {
    background-color: #0f172a;
}

/* Cards (Dashboard Stats, etc.) */
QFrame.CardFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 20px;
}

QLabel.CardTitle {
    color: #94a3b8;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

QLabel.CardValue {
    color: #ffffff;
    font-size: 28px;
    font-weight: bold;
}

/* Inputs & Form Fields */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 14px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #0f172a;
}

QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 14px;
    combobox-popup: 0;
}

QComboBox:focus {
    border: 1px solid #3b82f6;
}

QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #f8fafc;
}

/* Buttons */
QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #475569;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton.PrimaryButton {
    background-color: #2563eb; /* Blue 600 */
    border: none;
    color: #ffffff;
}

QPushButton.PrimaryButton:hover {
    background-color: #3b82f6;
}

QPushButton.PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton.DangerButton {
    background-color: #dc2626; /* Red 600 */
    border: none;
    color: #ffffff;
}

QPushButton.DangerButton:hover {
    background-color: #ef4444;
}

QPushButton.DangerButton:pressed {
    background-color: #b91c1c;
}

/* Dialogs */
QDialog {
    background-color: #0f172a;
    border: 1px solid #334155;
}

/* Custom Table Widget Styling */
QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    gridline-color: #334155;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #334155;
    selection-color: #3b82f6;
}

QTableWidget::item {
    padding: 10px;
}

QTableWidget::item:selected {
    background-color: #334155;
    border-left: 3px solid #3b82f6;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0f172a;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Calendar Widget (Custom date selector popup) */
QCalendarWidget QWidget {
    background-color: #1e293b;
    color: #f8fafc;
}

QCalendarWidget QMenu {
    background-color: #1e293b;
    color: #f8fafc;
}

QCalendarWidget QNavigationBar {
    background-color: #0f172a;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #f8fafc;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #475569;
}
"""
