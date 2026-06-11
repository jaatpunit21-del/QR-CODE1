from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame, 
    QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from utils.link_resolver import resolve_maps_url
from models.business import add_business, get_settings, get_business
from ui.qr_viewer import QRViewerDialog
from utils.logger import get_logger

logger = get_logger("ui.link_resolver")

class ResolveThread(QThread):
    """Background worker thread to resolve Google Maps redirect links and extract Place ID & name."""
    resolved = Signal(str, str, str, str) # Signals: review_url, business_name, place_id, error_message

    def __init__(self, target_url):
        super().__init__()
        self.target_url = target_url

    def run(self):
        review_url, business_name, error_msg = resolve_maps_url(self.target_url)
        if error_msg:
            self.resolved.emit("", "", "", error_msg)
        else:
            # Try to extract Place ID or CID for informational text in UI
            place_id = "Unknown"
            if "placeid=" in review_url:
                place_id = review_url.split("placeid=")[1]
            elif "cid=" in review_url:
                place_id = review_url.split("cid=")[1].split("&")[0]
            self.resolved.emit(review_url, business_name, place_id, "")


class LinkResolverWidget(QWidget):
    """Widget providing tool to extract direct Google Review URLs from normal Maps URLs."""
    
    create_profile_triggered = Signal(str) # Emitted with resolved URL to auto-populate BusinessDialog
    business_created_signal = Signal() # Emitted to tell other widgets (Dashboard/List) to refresh data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instant_qr_mode = False # Tracks if we should auto-save and launch viewer on finish
        self.resolved_name = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Title
        title_label = QLabel("Instant QR Code Generator")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)

        # Subtitle instructions
        desc_label = QLabel(
            "Paste a standard Google Maps link (e.g. copied from Google Maps app or search). "
            "Click 'Instant QR Code' to automatically extract the business details and get a ready-to-print flyer, "
            "or click 'Resolve' to check the links manually."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc_label)

        # Input Form Card
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(12)

        input_title = QLabel("PASTE GOOGLE MAPS LINK:")
        input_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #3b82f6; border: none;")
        input_layout.addWidget(input_title)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("e.g. https://maps.app.goo.gl/abCdEFG123 or https://www.google.com/maps/place/...")
        self.url_input.setStyleSheet("border-radius: 6px;")
        input_layout.addWidget(self.url_input)

        # Action Buttons Layout (Side by side)
        action_btn_layout = QHBoxLayout()
        action_btn_layout.setSpacing(10)

        # 1. Resolve Button
        self.resolve_btn = QPushButton("Resolve Details")
        self.resolve_btn.setStyleSheet("background-color: #4b5563; border: none; padding: 10px; font-weight: bold;")
        self.resolve_btn.clicked.connect(self.start_standard_resolution)
        
        # 2. Instant QR Button (Green Primary)
        self.instant_qr_btn = QPushButton("⚡ Generate Instant QR")
        self.instant_qr_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.instant_qr_btn.clicked.connect(self.start_instant_resolution)

        action_btn_layout.addWidget(self.resolve_btn)
        action_btn_layout.addWidget(self.instant_qr_btn)
        input_layout.addLayout(action_btn_layout)

        # Loading / Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Infinite spinner mode
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f172a;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        input_layout.addWidget(self.progress_bar)

        layout.addWidget(input_frame)

        # Result Panel Card (Hidden initially)
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #10b981; /* Green border for success */
                border-radius: 12px;
            }
        """)
        self.result_frame.setVisible(False)
        
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setContentsMargins(15, 15, 15, 15)
        result_layout.setSpacing(12)

        result_title = QLabel("RESOLVED DIRECT LINK:")
        result_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981; border: none;")
        result_layout.addWidget(result_title)

        self.result_url_input = QLineEdit()
        self.result_url_input.setReadOnly(True)
        self.result_url_input.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 8px; color: #f8fafc;"
        )
        result_layout.addWidget(self.result_url_input)

        self.place_id_lbl = QLabel("Place ID: None")
        self.place_id_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")
        result_layout.addWidget(self.place_id_lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.copy_btn = QPushButton("Copy Link")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        self.test_btn = QPushButton("Open & Test Review Dialog")
        self.test_btn.setStyleSheet("background-color: #10b981; color: white; border: none;")
        self.test_btn.clicked.connect(self.test_review_link)

        self.create_biz_btn = QPushButton("Create Business Profile")
        self.create_biz_btn.setProperty("class", "PrimaryButton")
        self.create_biz_btn.clicked.connect(self.trigger_profile_creation)

        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.create_biz_btn)
        result_layout.addLayout(btn_layout)

        layout.addWidget(self.result_frame)
        layout.addStretch()

    def start_standard_resolution(self):
        """Starts resolution process in standard detail display mode."""
        self.instant_qr_mode = False
        self.execute_resolution()

    def start_instant_resolution(self):
        """Starts resolution process in 1-click automatic profile creation mode."""
        self.instant_qr_mode = True
        self.execute_resolution()

    def execute_resolution(self):
        """Validates inputs and spawns QThread worker."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please paste a Google Maps link first.")
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Input Error", "Link must start with http:// or https://")
            return

        self.resolve_btn.setEnabled(False)
        self.instant_qr_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.result_frame.setVisible(False)

        # Start QThread
        self.thread = ResolveThread(url)
        self.thread.resolved.connect(self.on_resolved)
        self.thread.start()

    @Slot(str, str, str, str)
    def on_resolved(self, review_url, business_name, place_id, error_msg):
        """Triggered when background redirect thread completes."""
        self.resolve_btn.setEnabled(True)
        self.instant_qr_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if error_msg:
            QMessageBox.critical(self, "Resolution Failed", error_msg)
            return

        self.result_url_input.setText(review_url)
        self.resolved_name = business_name
        self.place_id_lbl.setText(f"Business: {business_name} | Place ID: {place_id}")
        
        if self.instant_qr_mode:
            # Trigger 1-click save and open viewer!
            self.generate_and_show_instant_qr(review_url, business_name)
        else:
            # Show standard details panel
            self.result_frame.setVisible(True)

    def generate_and_show_instant_qr(self, review_url, business_name):
        """Saves business record in background and opens the QR Dialog instantly."""
        try:
            # Save business to database (Dynamic redirect, 12 months)
            business_id = add_business(
                name=business_name,
                review_url=review_url,
                address="",
                contact_info="",
                logo_path="",
                qr_mode="Dynamic",
                subscription_duration="12 months"
            )
            
            # Fetch redirect setting url
            settings = get_settings()
            redirect_url = settings.get("redirect_base_url", "http://localhost:5050")
            
            # Retrieve newly inserted profile dictionary
            biz_data = get_business(business_id)
            
            # Notify database list to update grids
            self.business_created_signal.emit()
            
            # Launch QR viewer immediately
            dialog = QRViewerDialog(self, business_data=biz_data, redirect_base_url=redirect_url)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error generating instant QR profile: {e}")
            QMessageBox.critical(self, "Database Error", f"Failed to save profile: {e}")

    def copy_to_clipboard(self):
        """Copies link to OS clipboard."""
        QApplication.clipboard().setText(self.result_url_input.text())
        QMessageBox.information(self, "Copied", "Direct review link copied to clipboard!")

    def test_review_link(self):
        """Opens link in default browser."""
        url = self.result_url_input.text()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def trigger_profile_creation(self):
        """Signals parent GUI to transition and create a business profile using this URL."""
        url = self.result_url_input.text()
        if url:
            self.create_profile_triggered.emit(url)
