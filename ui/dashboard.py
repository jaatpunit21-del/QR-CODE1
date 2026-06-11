import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFileDialog, QMessageBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from models.business import get_dashboard_stats, get_settings
from utils.logger import get_logger

logger = get_logger("ui.dashboard")

class KPICard(QFrame):
    """A reusable, styled card widget for displaying KPI statistics."""
    
    def __init__(self, title, value, color="#ffffff", parent=None):
        super().__init__(parent)
        self.setObjectName("KPICard")
        self.setProperty("class", "CardFrame")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setProperty("class", "CardTitle")
        self.title_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        
        self.val_lbl = QLabel(str(value))
        self.val_lbl.setProperty("class", "CardValue")
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)

    def update_value(self, value):
        """Updates the numeric display value of the card."""
        self.val_lbl.setText(str(value))


class DashboardWidget(QWidget):
    """Widget displaying business status summary, alert listings, and report options."""
    
    navigate_to_businesses = Signal() # Signal to change view to business tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_dashboard()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Section
        header_layout = QHBoxLayout()
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Export Report Button
        self.export_report_btn = QPushButton("Export CSV Report")
        self.export_report_btn.setStyleSheet("""
            padding: 8px 16px;
            background-color: #10b981; /* Green 500 */
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: bold;
        """)
        self.export_report_btn.clicked.connect(self.export_csv_report)
        header_layout.addWidget(self.export_report_btn)
        
        layout.addLayout(header_layout)

        # 4 KPI Cards Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        self.card_total = KPICard("Total Businesses", "0", "#ffffff")
        self.card_active = KPICard("Active Subscriptions", "0", "#10b981") # Green
        self.card_expiring = KPICard("Expiring Soon (30d)", "0", "#f59e0b") # Amber/Orange
        self.card_expired = KPICard("Expired Subscriptions", "0", "#ef4444") # Red
        
        grid_layout.addWidget(self.card_total, 0, 0)
        grid_layout.addWidget(self.card_active, 0, 1)
        grid_layout.addWidget(self.card_expiring, 0, 2)
        grid_layout.addWidget(self.card_expired, 0, 3)
        
        layout.addLayout(grid_layout)
        
        # Alert Table Section
        alerts_frame = QFrame()
        alerts_frame.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        alerts_layout = QVBoxLayout(alerts_frame)
        alerts_layout.setContentsMargins(15, 15, 15, 15)
        alerts_layout.setSpacing(10)
        
        alert_title = QLabel("Expiring Soon Alert")
        alert_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f59e0b; border: none;")
        alerts_layout.addWidget(alert_title)
        
        # Table of businesses expiring soon
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(3)
        self.alert_table.setHorizontalHeaderLabels(["Business Name", "Expiration Date", "Days Remaining"])
        self.alert_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.alert_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.alert_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.alert_table.setStyleSheet("border: none; background-color: #1e293b;")
        self.alert_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.alert_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        alerts_layout.addWidget(self.alert_table)
        
        # Button to go to business profiles
        self.view_all_btn = QPushButton("Go to Business Profiles")
        self.view_all_btn.setStyleSheet("background-color: #334155; border: none; padding: 6px;")
        self.view_all_btn.clicked.connect(self.navigate_to_businesses.emit)
        alerts_layout.addWidget(self.view_all_btn)
        
        layout.addWidget(alerts_frame)
        layout.addStretch()

    def refresh_dashboard(self):
        """Fetches data from database and refreshes KPI cards and alerts table."""
        stats = get_dashboard_stats()
        
        # Update cards
        self.card_total.update_value(stats['total'])
        self.card_active.update_value(stats['active'])
        self.card_expiring.update_value(stats['expiring_soon'])
        self.card_expired.update_value(stats['expired'])
        
        # Update alerts list table
        self.populate_alerts_table(stats['expiring_list'])

    def populate_alerts_table(self, expiring_list):
        """Populates the expiring-soon alert grid."""
        self.alert_table.setRowCount(0)
        
        for idx, biz in enumerate(expiring_list):
            self.alert_table.insertRow(idx)
            
            # Name
            self.alert_table.setItem(idx, 0, QTableWidgetItem(biz['name']))
            
            # Expiration
            exp_date_str = biz['expiration_date']
            self.alert_table.setItem(idx, 1, QTableWidgetItem(exp_date_str))
            
            # Days Remaining
            days_left = 0
            if exp_date_str:
                try:
                    exp_date = datetime.strptime(exp_date_str[:10], "%Y-%m-%d")
                    delta = exp_date - datetime.now()
                    days_left = max(0, delta.days + 1)
                except Exception as e:
                    logger.error(f"Error parsing date {exp_date_str}: {e}")
            
            days_item = QTableWidgetItem(f"{days_left} days")
            days_item.setTextAlignment(Qt.AlignCenter)
            self.alert_table.setItem(idx, 2, days_item)

    def export_csv_report(self):
        """Generates a complete business CSV directory report."""
        from models.business import list_businesses
        businesses = list_businesses()
        
        if not businesses:
            QMessageBox.warning(self, "Export Report", "There are no businesses in the database to export.")
            return
            
        default_name = f"qr_review_manager_report_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Report", default_name, "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # Write Header Row
                    writer.writerow([
                        "Business Name", "Address", "Contact Information", 
                        "Google Review URL", "QR Identifier", "QR Mode", 
                        "Subscription Duration", "Expiration Date", "Status", "Created At"
                    ])
                    
                    # Write Data Rows
                    for biz in businesses:
                        writer.writerow([
                            biz['name'],
                            biz.get('address', ''),
                            biz.get('contact_info', ''),
                            biz['review_url'],
                            biz['qr_identifier'],
                            biz.get('qr_mode', 'Dynamic'),
                            biz.get('subscription_duration', ''),
                            biz.get('expiration_date', ''),
                            biz['status'],
                            biz.get('created_at', '')
                        ])
                        
                QMessageBox.information(
                    self, "Export Successful", 
                    f"Business report successfully exported to:\n{file_path}"
                )
            except Exception as e:
                logger.error(f"Failed to export CSV report: {e}")
                QMessageBox.critical(self, "Export Failed", f"An error occurred while exporting the report:\n{e}")
