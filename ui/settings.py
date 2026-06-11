import socket
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFileDialog, 
    QSpinBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal
from models.business import get_settings, save_setting
from database.connection import backup_database, restore_database
from utils.logger import get_logger

logger = get_logger("ui.settings")

class SettingsWidget(QWidget):
    """Widget allowing system administration, backup/restore, and URL configuration."""
    
    settings_changed = Signal() # Emitted when redirect URL or other settings change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()

    def get_local_ip(self):
        """Discovers the computer's local network IP address on the primary active interface."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connecting to a public IP doesn't send packets, but forces OS to resolve local interface IP
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Title
        title_label = QLabel("Settings & Configuration")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)

        # 1. Server Configuration Group
        server_group = QGroupBox("Server Settings")
        server_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #3b82f6; /* Blue 500 */
                border: 1px solid #334155;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        server_layout = QFormLayout(server_group)
        server_layout.setSpacing(12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:5000 or https://yourdomain.com")
        self.url_input.setToolTip(
            "This URL will be baked into the dynamic QR codes. If testing on local network, "
            "use your PC's local IP address (e.g. http://192.168.1.50:5000)."
        )
        server_layout.addRow("Redirect Server Base URL *", self.url_input)

        self.days_input = QSpinBox()
        self.days_input.setRange(1, 365)
        self.days_input.setValue(30)
        server_layout.addRow("'Expiring Soon' Range (Days)", self.days_input)

        # Save Server Settings Button
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.setProperty("class", "PrimaryButton")
        self.save_settings_btn.clicked.connect(self.save_server_settings)
        server_layout.addRow("", self.save_settings_btn)

        layout.addWidget(server_group)

        # 2. Local Testing Diagnostics Group
        diag_group = QGroupBox("Mobile Test Center")
        diag_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #10b981; /* Green 500 */
                border: 1px solid #334155;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        diag_layout = QVBoxLayout(diag_group)
        diag_layout.setSpacing(10)

        local_ip = self.get_local_ip()
        
        info_text = (
            f"<b>Local Network IP:</b> {local_ip}<br><br>"
            "To test dynamic QR codes from a smartphone:<br>"
            "1. Connect your smartphone and PC to the same Wi-Fi network.<br>"
            "2. Set the <b>Redirect Server Base URL</b> above to: "
            f"<code>http://{local_ip}:3000</code> and click Save.<br>"
            "3. Generate and scan the QR code. It will access this computer's local redirect server."
        )
        self.info_lbl = QLabel(info_text)
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.5; padding: 5px;")
        diag_layout.addWidget(self.info_lbl)
        
        layout.addWidget(diag_group)

        # 3. Database Management Group (Backup / Restore)
        db_group = QGroupBox("Database Maintenance")
        db_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #ef4444; /* Red 500 */
                border: 1px solid #334155;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)
        db_layout = QHBoxLayout(db_group)
        db_layout.setContentsMargins(15, 15, 15, 15)
        db_layout.setSpacing(15)

        self.backup_btn = QPushButton("Backup Database")
        self.backup_btn.setStyleSheet("background-color: #334155; border: none; padding: 10px;")
        self.backup_btn.clicked.connect(self.backup_db)
        
        self.restore_btn = QPushButton("Restore Database")
        self.restore_btn.setProperty("class", "DangerButton")
        self.restore_btn.setStyleSheet("padding: 10px;")
        self.restore_btn.clicked.connect(self.restore_db)

        db_layout.addWidget(self.backup_btn)
        db_layout.addWidget(self.restore_btn)
        
        layout.addWidget(db_group)
        layout.addStretch()

    def load_settings(self):
        """Loads configuration from the database into inputs."""
        settings = get_settings()
        self.url_input.setText(settings.get("redirect_base_url", "http://localhost:3000"))
        self.days_input.setValue(int(settings.get("expiring_soon_days", 30)))

    def save_server_settings(self):
        """Saves current server fields to SQLite."""
        url = self.url_input.text().strip()
        days = self.days_input.value()
        
        if not url:
            QMessageBox.warning(self, "Validation Error", "Redirect Server Base URL cannot be empty.")
            return
            
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Validation Error", "URL must start with http:// or https://")
            return
            
        save_setting("redirect_base_url", url)
        save_setting("expiring_soon_days", str(days))
        
        self.settings_changed.emit()
        QMessageBox.information(self, "Settings Saved", "System configuration saved successfully!")

    def backup_db(self):
        """Trigger database backup routine."""
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Backup Target Folder")
        if dest_dir:
            try:
                dest_path = backup_database(dest_dir)
                filename = os.path.basename(dest_path)
                QMessageBox.information(
                    self, "Backup Success", 
                    f"Database backup saved successfully to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Failed to backup database:\n{e}")

    def restore_db(self):
        """Trigger database restore sequence with confirmation safety check."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup Database File", "", "SQLite DB Files (*.db)"
        )
        if file_path:
            reply = QMessageBox.question(
                self, "Confirm Restore", 
                "WARNING: Restoring the database will overwrite all your current business and QR profiles.\n\n"
                "This action cannot be undone. Do you wish to proceed?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    restore_database(file_path)
                    QMessageBox.information(
                        self, "Restore Success", 
                        "Database restored successfully!\n"
                        "The application will now refresh database bindings."
                    )
                    self.load_settings()
                    self.settings_changed.emit() # Triggers main layout rebuild
                except Exception as e:
                    QMessageBox.critical(self, "Restore Failed", f"Failed to restore database:\n{e}")
