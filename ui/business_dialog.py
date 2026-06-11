import os
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QComboBox, QDateEdit, 
    QLabel, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt
from utils.logger import get_logger

logger = get_logger("ui.business_dialog")

class BusinessDialog(QDialog):
    """Dialog for adding or editing a business profile."""
    
    def __init__(self, parent=None, business_data=None, initial_url=None):
        super().__init__(parent)
        self.business_data = business_data
        self.is_edit = business_data is not None
        self.initial_url = initial_url
        
        self.setWindowTitle("Edit Business Profile" if self.is_edit else "Add New Business")
        self.setMinimumWidth(500)
        self.resize(500, 450)
        
        self.init_ui()
        if self.is_edit:
            self.load_business_data()
        elif self.initial_url:
            self.url_input.setText(self.initial_url)
            
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title header
        self.header_label = QLabel("Edit Business Profile" if self.is_edit else "Add New Business")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; margin-bottom: 15px;")
        layout.addWidget(self.header_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Five Star Pizza")
        form_layout.addRow("Business Name *", self.name_input)
        
        # Google Review URL
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://g.page/r/... or https://maps.google.com/...")
        form_layout.addRow("Google Review URL *", self.url_input)
        
        # Address
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g. 123 Main St, New York, NY")
        form_layout.addRow("Address", self.address_input)
        
        # Contact Info
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("e.g. contact@fivestarpizza.com or +1 555-0199")
        form_layout.addRow("Contact Info", self.contact_input)
        
        # Logo path
        logo_layout = QHBoxLayout()
        self.logo_input = QLineEdit()
        self.logo_input.setPlaceholderText("Optional path to business logo")
        self.logo_input.setReadOnly(True)
        self.browse_logo_btn = QPushButton("Browse")
        self.browse_logo_btn.clicked.connect(self.browse_logo)
        logo_layout.addWidget(self.logo_input)
        logo_layout.addWidget(self.browse_logo_btn)
        form_layout.addRow("Business Logo", logo_layout)
        
        # QR Mode
        self.qr_mode_select = QComboBox()
        self.qr_mode_select.addItems(["Dynamic", "Direct"])
        self.qr_mode_select.setToolTip(
            "Dynamic QR codes allow subscription deactivation and updating the URL. "
            "Direct QR codes route directly to Google and cannot be disabled once printed."
        )
        form_layout.addRow("QR Code Type", self.qr_mode_select)
        
        # Subscription Duration
        self.duration_select = QComboBox()
        self.duration_select.addItems([
            "1 month", 
            "3 months", 
            "6 months", 
            "12 months", 
            "No expiration", 
            "Custom date"
        ])
        self.duration_select.setCurrentText("12 months")
        self.duration_select.currentTextChanged.connect(self.on_duration_changed)
        form_layout.addRow("How long should this QR remain active? *", self.duration_select)
        
        # Custom Date Edit (Hidden by default, shown when 'Custom date' is selected)
        self.custom_date_label = QLabel("Expiration Date:")
        self.custom_date_edit = QDateEdit()
        self.custom_date_edit.setCalendarPopup(True)
        self.custom_date_edit.setDate(QDate.currentDate().addDays(30))
        self.custom_date_edit.setMinimumDate(QDate.currentDate())
        
        form_layout.addRow(self.custom_date_label, self.custom_date_edit)
        self.toggle_custom_date_visibility(False)
        
        layout.addLayout(form_layout)
        layout.addSpacing(20)
        
        # Dialog Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save & Generate QR" if not self.is_edit else "Save Changes")
        self.save_btn.setProperty("class", "PrimaryButton")
        self.save_btn.clicked.connect(self.validate_and_save)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        
    def browse_logo(self):
        """Opens file dialog to select a business logo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Business Logo", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.logo_input.setText(file_path)
            
    def toggle_custom_date_visibility(self, visible):
        """Shows or hides the custom date picker controls."""
        self.custom_date_label.setVisible(visible)
        self.custom_date_edit.setVisible(visible)
        
    def on_duration_changed(self, text):
        """Triggered when duration dropdown selection changes."""
        self.toggle_custom_date_visibility(text == "Custom date")
        
    def load_business_data(self):
        """Loads business data to populate fields in edit mode."""
        data = self.business_data
        self.name_input.setText(data['name'])
        self.url_input.setText(data['review_url'])
        self.address_input.setText(data.get('address', ''))
        self.contact_input.setText(data.get('contact_info', ''))
        self.logo_input.setText(data.get('logo_path', ''))
        self.qr_mode_select.setCurrentText(data.get('qr_mode', 'Dynamic'))
        
        # Determine duration selection mapping
        db_duration = data.get('subscription_duration', '')
        expiration_date = data.get('expiration_date', '')
        
        if db_duration in ["1 month", "3 months", "6 months", "12 months", "No expiration"]:
            self.duration_select.setCurrentText(db_duration)
        else:
            self.duration_select.setCurrentText("Custom date")
            if expiration_date:
                qdate = QDate.fromString(expiration_date[:10], "yyyy-MM-dd")
                if qdate.isValid():
                    self.custom_date_edit.setDate(qdate)
                    
    def get_form_data(self):
        """Extracts and formats data from the dialog fields."""
        duration = self.duration_select.currentText()
        expiration_date = ""
        
        if duration == "Custom date":
            expiration_date = self.custom_date_edit.date().toString("yyyy-MM-dd")
        elif duration != "No expiration":
            # Calculated duration
            from models.business import calculate_expiration_date
            expiration_date = calculate_expiration_date(duration)
            
        # Determine active status dynamically based on current date vs expiration date
        status = "Active"
        if expiration_date:
            today_str = datetime.now().strftime("%Y-%m-%d")
            if expiration_date < today_str:
                status = "Expired"
                
        return {
            "name": self.name_input.text().strip(),
            "review_url": self.url_input.text().strip(),
            "address": self.address_input.text().strip(),
            "contact_info": self.contact_input.text().strip(),
            "logo_path": self.logo_input.text().strip(),
            "qr_mode": self.qr_mode_select.currentText(),
            "subscription_duration": duration,
            "expiration_date": expiration_date,
            "status": status
        }
        
    def validate_and_save(self):
        """Validates input fields, auto-resolves Google Maps links, and accepts the dialog."""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Business Name is required.")
            self.name_input.setFocus()
            return
            
        if not url:
            QMessageBox.warning(self, "Validation Error", "Google Review URL is required.")
            self.url_input.setFocus()
            return
            
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(
                self, "Validation Error", 
                "Invalid Google Review URL format. Please start with http:// or https://"
            )
            self.url_input.setFocus()
            return
            
        # Automatically resolve standard Google Maps links to direct review dialog links
        if "writereview" not in url and ("maps.google" in url or "maps.app.goo.gl" in url or "/maps/" in url):
            from PySide6.QtWidgets import QApplication
            from utils.link_resolver import resolve_maps_url
            
            self.save_btn.setText("Resolving Maps Link...")
            self.save_btn.setEnabled(False)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents() # Refresh GUI elements
            
            try:
                resolved_url, extracted_name, error = resolve_maps_url(url)
                if error:
                    QMessageBox.warning(
                        self, "Link Helper Notice", 
                        f"Could not convert Google Maps link automatically to a direct review link:\n{error}\n\n"
                        "Saving original link anyway."
                    )
                else:
                    if resolved_url:
                        url = resolved_url
                        self.url_input.setText(resolved_url)
                    if extracted_name and not self.name_input.text().strip():
                        self.name_input.setText(extracted_name)
                        # We also update our name variable since it is checked at the beginning of validation
                        name = extracted_name
            except Exception as e:
                logger.error(f"Error during inline link resolution: {e}")
            finally:
                self.save_btn.setText("Save Changes" if self.is_edit else "Save & Generate QR")
                self.save_btn.setEnabled(True)
                QApplication.restoreOverrideCursor()

        self.accept()
