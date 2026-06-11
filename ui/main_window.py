import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QFrame, QPushButton, QStackedWidget, QLabel, 
    QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from ui.dashboard import DashboardWidget
from ui.business_list import BusinessListWidget
from ui.settings import SettingsWidget
from ui.link_resolver import LinkResolverWidget
from ui.styles import DARK_STYLE_SHEET
from server.redirect_server import RedirectServerThread
from models.business import update_expired_statuses, get_settings
from utils.logger import get_logger

logger = get_logger("ui.main_window")

class MainWindow(QMainWindow):
    """Orchestrates layout views, routing channels, and background servers."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QR Review Manager")
        self.setMinimumSize(1000, 650)
        self.resize(1100, 700)
        
        # Apply premium QSS styles
        self.setStyleSheet(DARK_STYLE_SHEET)
        
        # Sync business expired statuses on startup
        update_expired_statuses()
        
        # Initialize sub-views
        self.dashboard_widget = DashboardWidget()
        self.business_list_widget = BusinessListWidget()
        self.settings_widget = SettingsWidget()
        self.link_resolver_widget = LinkResolverWidget()
        
        self.init_ui()
        self.connect_signals()
        self.start_local_server()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- 1. SIDEBAR PANEL ---
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 25)
        sidebar_layout.setSpacing(10)
        
        # Sidebar Logo Header
        sidebar_logo_lbl = QLabel("⭐ 5-Star QR")
        sidebar_logo_lbl.setObjectName("SidebarTitle")
        sidebar_logo_lbl.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #3b82f6; 
            margin-bottom: 25px; 
            padding: 5px;
        """)
        sidebar_layout.addWidget(sidebar_logo_lbl)
        
        # Nav Buttons (exclusive check states)
        self.btn_dashboard = QPushButton("  Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)
        self.btn_dashboard.setProperty("class", "NavButton")
        self.btn_dashboard.clicked.connect(lambda: self.navigate_to(0))
        
        self.btn_businesses = QPushButton("  Businesses")
        self.btn_businesses.setCheckable(True)
        self.btn_businesses.setProperty("class", "NavButton")
        self.btn_businesses.clicked.connect(lambda: self.navigate_to(1))
        
        self.btn_resolver = QPushButton("  Link Helper")
        self.btn_resolver.setCheckable(True)
        self.btn_resolver.setProperty("class", "NavButton")
        self.btn_resolver.clicked.connect(lambda: self.navigate_to(3))
        
        self.btn_settings = QPushButton("  Settings")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setProperty("class", "NavButton")
        self.btn_settings.clicked.connect(lambda: self.navigate_to(2))
        
        # Exclusive check grouping manually
        self.nav_buttons = [self.btn_dashboard, self.btn_businesses, self.btn_settings, self.btn_resolver]
        
        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_businesses)
        sidebar_layout.addWidget(self.btn_resolver)
        sidebar_layout.addWidget(self.btn_settings)
        
        sidebar_layout.addStretch()
        
        # System version footer
        version_lbl = QLabel("v1.0.0")
        version_lbl.setStyleSheet("color: #475569; font-size: 11px; padding-left: 5px;")
        sidebar_layout.addWidget(version_lbl)
        
        main_layout.addWidget(sidebar)
        
        # --- 2. STACKED CENTRAL WIDGETS ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("ContentStackedWidget")
        
        self.stacked_widget.addWidget(self.dashboard_widget)      # Index 0
        self.stacked_widget.addWidget(self.business_list_widget)  # Index 1
        self.stacked_widget.addWidget(self.settings_widget)       # Index 2
        self.stacked_widget.addWidget(self.link_resolver_widget)  # Index 3
        
        main_layout.addWidget(self.stacked_widget, stretch=1)
        
        # --- 3. STATUS BAR ---
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1e293b;
                color: #94a3b8;
                border-top: 1px solid #334155;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        self.setStatusBar(self.status_bar)
        
        self.server_status_lbl = QLabel("Local Server: Initializing...")
        self.server_status_lbl.setStyleSheet("font-size: 11px; padding: 2px 10px; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.server_status_lbl)
        self.status_bar.showMessage("System ready.", 3000)

    def connect_signals(self):
        """Ties signal relays between widget layouts."""
        # Route dashboard shortcut trigger to business profiles stack
        self.dashboard_widget.navigate_to_businesses.connect(
            lambda: self.navigate_to(1)
        )
        
        # Refresh dashboard stats when businesses table changes
        self.business_list_widget.business_updated.connect(
            self.dashboard_widget.refresh_dashboard
        )
        
        # Force refresh widgets when settings base url updates
        self.settings_widget.settings_changed.connect(self.on_settings_reloaded)
        
        # Connect the link helper creation trigger
        self.link_resolver_widget.create_profile_triggered.connect(
            self.on_resolver_create_profile
        )
        self.link_resolver_widget.business_created_signal.connect(
            self.on_settings_reloaded
        )

    def navigate_to(self, index):
        """Swaps active stacked frame and syncs sidebar button check states."""
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            
        # Refresh widgets on load to display fresh database states
        if index == 0:
            self.dashboard_widget.refresh_dashboard()
        elif index == 1:
            self.business_list_widget.refresh_data()
        elif index == 2:
            self.settings_widget.load_settings()

    def start_local_server(self):
        """Boots the background Flask redirection thread."""
        try:
            # Check port (defaults to 3000)
            self.server_thread = RedirectServerThread(host="0.0.0.0", port=3000)
            self.server_thread.server_error.connect(self.on_server_error)
            self.server_thread.start()
            
            self.server_status_lbl.setText("● Local Server Online (Port 3000)")
            self.server_status_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
            logger.info("Redirect server QThread initialized successfully.")
        except Exception as e:
            self.on_server_error(str(e))
 
    @Slot(str)
    def on_server_error(self, err_msg):
        """Handler for redirect server startup errors."""
        self.server_status_lbl.setText("● Local Server Offline")
        self.server_status_lbl.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold;")
        logger.error(f"Redirect server reported crash status: {err_msg}")
        QMessageBox.critical(
            self, "Network Server Error", 
            f"Failed to start the background redirect server:\n{err_msg}\n\n"
            "Testing dynamic QR codes locally will not function until resolved. "
            "Verify port 3000 is not in use."
        )

    def on_settings_reloaded(self):
        """Invoked when settings update, refreshes active grids."""
        self.dashboard_widget.refresh_dashboard()
        self.business_list_widget.refresh_data()

    @Slot(str)
    def on_resolver_create_profile(self, url):
        """Switches to businesses view and opens creation form pre-filled with resolved review URL."""
        self.navigate_to(1)
        self.business_list_widget.open_add_dialog(initial_url=url)

    def closeEvent(self, event):
        """Catches exit sequence and terminates active thread services safely."""
        logger.info("Application shutting down. Terminating background threads...")
        # Since RedirectServerThread is launched as a daemon thread,
        # it will automatically terminate when Python shuts down, but we can explicitly log it.
        event.accept()
