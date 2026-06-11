from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QLineEdit, QPushButton, QComboBox, 
    QLabel, QHeaderView, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from models.business import list_businesses, add_business, update_business, delete_business, get_settings
from ui.business_dialog import BusinessDialog
from ui.qr_viewer import QRViewerDialog
from utils.logger import get_logger

logger = get_logger("ui.business_list")

class BusinessListWidget(QWidget):
    """Widget displaying a searchable, filterable grid of managed businesses."""
    
    business_updated = Signal() # Signal emitted when database is changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        title_label = QLabel("Manage Businesses")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)

        # Filter & Action Bar
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, address, or contact...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.refresh_data)
        action_layout.addWidget(self.search_input)

        # Status Filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Active", "Expired"])
        self.status_filter.currentTextChanged.connect(self.refresh_data)
        action_layout.addWidget(self.status_filter)

        action_layout.addStretch()

        # Add New Business Button
        self.add_btn = QPushButton("Add Business")
        self.add_btn.setProperty("class", "PrimaryButton")
        self.add_btn.clicked.connect(self.open_add_dialog)
        action_layout.addWidget(self.add_btn)

        layout.addLayout(action_layout)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Business Name", "Contact Details", "QR Mode", 
            "Expiration Date", "Status", "Actions"
        ])
        
        # Configure Table Headers to resize beautifully
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                alternate-background-color: #1a2333;
            }
        """)
        
        layout.addWidget(self.table)

    def refresh_data(self):
        """Loads and lists businesses using search query and status filters."""
        search = self.search_input.text().strip()
        status_text = self.status_filter.currentText()
        
        # Normalize status filter
        status_filter = "All"
        if status_text == "Active":
            status_filter = "Active"
        elif status_text == "Expired":
            status_filter = "Expired"
            
        businesses = list_businesses(search_query=search, status_filter=status_filter)
        self.populate_table(businesses)

    def populate_table(self, businesses):
        """Populates rows into the business QTableWidget."""
        self.table.setRowCount(0)
        self.business_list = businesses # Store internal cache of current list
        
        for idx, biz in enumerate(businesses):
            self.table.insertRow(idx)
            
            # 1. Business Name
            name_item = QTableWidgetItem(biz['name'])
            name_item.setData(Qt.UserRole, biz['id']) # Store ID inside item
            self.table.setItem(idx, 0, name_item)
            
            # 2. Contact Details
            contact_text = biz['contact_info'] if biz['contact_info'] else "N/A"
            contact_item = QTableWidgetItem(contact_text)
            self.table.setItem(idx, 1, contact_item)
            
            # 3. QR Mode
            mode_item = QTableWidgetItem(biz.get('qr_mode', 'Dynamic'))
            mode_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 2, mode_item)
            
            # 4. Expiration Date
            exp_date = biz['expiration_date'] if biz['expiration_date'] else "Lifetime"
            exp_item = QTableWidgetItem(exp_date)
            exp_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 3, exp_item)
            
            # 5. Status Badge Label
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(10, 2, 10, 2)
            status_layout.setAlignment(Qt.AlignCenter)
            
            status_label = QLabel(biz['status'])
            status_label.setAlignment(Qt.AlignCenter)
            
            if biz['status'] == 'Active':
                status_label.setStyleSheet("""
                    color: #10b981; 
                    background-color: rgba(16, 185, 129, 0.15); 
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-weight: bold;
                    font-size: 11px;
                """)
            else:
                status_label.setStyleSheet("""
                    color: #ef4444; 
                    background-color: rgba(239, 68, 68, 0.15); 
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-weight: bold;
                    font-size: 11px;
                """)
                
            status_layout.addWidget(status_label)
            self.table.setCellWidget(idx, 4, status_widget)
            
            # 6. Action Buttons Container
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            qr_btn = QPushButton("QR")
            qr_btn.setToolTip("View/Export QR Code")
            qr_btn.setStyleSheet("padding: 4px 8px; font-size: 12px; background-color: #2563eb; color: white; border: none;")
            qr_btn.clicked.connect(lambda checked=False, b_id=biz['id']: self.view_qr_code(b_id))
            
            edit_btn = QPushButton("Edit")
            edit_btn.setToolTip("Edit Business Profile")
            edit_btn.setStyleSheet("padding: 4px 8px; font-size: 12px; background-color: #4b5563; color: white; border: none;")
            edit_btn.clicked.connect(lambda checked=False, b_id=biz['id']: self.open_edit_dialog(b_id))
            
            del_btn = QPushButton("Del")
            del_btn.setToolTip("Delete Business Profile")
            del_btn.setStyleSheet("padding: 4px 8px; font-size: 12px; background-color: #dc2626; color: white; border: none;")
            del_btn.clicked.connect(lambda checked=False, b_id=biz['id']: self.delete_business_profile(b_id))
            
            actions_layout.addWidget(qr_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)
            
            self.table.setCellWidget(idx, 5, actions_widget)

    def open_add_dialog(self, initial_url=None):
        """Launches the Business dialog to add a new business profile."""
        dialog = BusinessDialog(self, initial_url=initial_url)
        if dialog.exec() == BusinessDialog.Accepted:
            data = dialog.get_form_data()
            try:
                add_business(
                    name=data['name'],
                    review_url=data['review_url'],
                    address=data['address'],
                    contact_info=data['contact_info'],
                    logo_path=data['logo_path'],
                    qr_mode=data['qr_mode'],
                    subscription_duration=data['subscription_duration'],
                    expiration_date=data['expiration_date'],
                    status=data['status']
                )
                self.refresh_data()
                self.business_updated.emit()
                QMessageBox.information(self, "Success", f"Business '{data['name']}' saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to add business: {e}")

    def open_edit_dialog(self, business_id):
        """Launches the Business dialog to edit an existing business profile."""
        # Find business data in the cache
        biz_data = next((b for b in self.business_list if b['id'] == business_id), None)
        if not biz_data:
            return
            
        dialog = BusinessDialog(self, business_data=biz_data)
        if dialog.exec() == BusinessDialog.Accepted:
            data = dialog.get_form_data()
            try:
                update_business(
                    business_id=business_id,
                    name=data['name'],
                    review_url=data['review_url'],
                    address=data['address'],
                    contact_info=data['contact_info'],
                    logo_path=data['logo_path'],
                    qr_mode=data['qr_mode'],
                    subscription_duration=data['subscription_duration'],
                    expiration_date=data['expiration_date'],
                    status=data['status']
                )
                self.refresh_data()
                self.business_updated.emit()
                QMessageBox.information(self, "Success", f"Business '{data['name']}' updated successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to update business: {e}")

    def delete_business_profile(self, business_id):
        """Prompts confirmation and deletes a business from database."""
        biz_data = next((b for b in self.business_list if b['id'] == business_id), None)
        if not biz_data:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to permanently delete the profile for '{biz_data['name']}'?\n"
            "This will break any dynamic QR codes pointing to this profile.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                delete_business(business_id)
                self.refresh_data()
                self.business_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete business: {e}")

    def view_qr_code(self, business_id):
        """Opens the QRViewerDialog for the selected business."""
        biz_data = next((b for b in self.business_list if b['id'] == business_id), None)
        if not biz_data:
            return
            
        settings = get_settings()
        redirect_base_url = settings.get("redirect_base_url", "http://localhost:5000")
        
        dialog = QRViewerDialog(self, business_data=biz_data, redirect_base_url=redirect_base_url)
        dialog.exec()
