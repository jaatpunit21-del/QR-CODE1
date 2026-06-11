import os
from io import BytesIO
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QMessageBox, QLineEdit
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from utils.qr_generator import generate_qr_image, export_png, export_svg, export_pdf
from utils.logger import get_logger

logger = get_logger("ui.qr_viewer")

class QRViewerDialog(QDialog):
    """Dialog for displaying and exporting a business's QR Code."""
    
    def __init__(self, parent=None, business_data=None, redirect_base_url="http://localhost:5000"):
        super().__init__(parent)
        self.business_data = business_data
        self.redirect_base_url = redirect_base_url
        
        self.setWindowTitle(f"QR Code - {business_data['name']}")
        self.setMinimumWidth(450)
        self.setMinimumHeight(550)
        
        # Determine target QR URL
        self.qr_url = self.calculate_qr_url()
        
        self.init_ui()
        self.load_qr_preview()

    def calculate_qr_url(self):
        """Calculates the target URL coded inside the QR image based on QR mode."""
        mode = self.business_data.get('qr_mode', 'Dynamic')
        if mode == 'Direct':
            url = self.business_data['review_url']
            logger.info(f"Direct QR Code generated pointing to: {url}")
            return url
        else:
            # Dynamic redirect through our server
            url = f"{self.redirect_base_url.rstrip('/')}/r/{self.business_data['qr_identifier']}"
            logger.info(f"Dynamic QR Code generated pointing to: {url}")
            return url

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Business Name Label
        self.title_label = QLabel(self.business_data['name'])
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # QR Mode Sub-Label
        mode_text = f"Mode: {self.business_data.get('qr_mode', 'Dynamic')} Link"
        mode_color = "#3b82f6" if self.business_data.get('qr_mode', 'Dynamic') == "Dynamic" else "#10b981"
        self.mode_label = QLabel(mode_text)
        self.mode_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {mode_color};")
        self.mode_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mode_label)
        
        # QR Code Image Frame / Label
        self.qr_image_label = QLabel()
        self.qr_image_label.setFixedSize(260, 260)
        self.qr_image_label.setStyleSheet(
            "background-color: white; border: 1px solid #334155; border-radius: 12px; padding: 10px;"
        )
        self.qr_image_label.setAlignment(Qt.AlignCenter)
        
        # Center QR code
        qr_layout = QHBoxLayout()
        qr_layout.addStretch()
        qr_layout.addWidget(self.qr_image_label)
        qr_layout.addStretch()
        layout.addLayout(qr_layout)
        
        # Display the Destination URL (Read-only)
        url_label = QLabel("QR Destination URL:")
        url_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(url_label)
        
        self.url_display = QLineEdit(self.qr_url)
        self.url_display.setReadOnly(True)
        self.url_display.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 6px; color: #cbd5e1;"
        )
        layout.addWidget(self.url_display)
        
        layout.addSpacing(10)
        
        # Export Actions Label
        export_label = QLabel("Export QR Code:")
        export_label.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
        layout.addWidget(export_label)
        
        # Export Buttons Layout
        export_btn_layout = QHBoxLayout()
        export_btn_layout.setSpacing(10)
        
        self.png_btn = QPushButton("PNG")
        self.png_btn.clicked.connect(self.export_png_file)
        
        self.svg_btn = QPushButton("SVG")
        self.svg_btn.clicked.connect(self.export_svg_file)
        
        self.pdf_btn = QPushButton("PDF Flyer")
        self.pdf_btn.setProperty("class", "PrimaryButton")
        self.pdf_btn.clicked.connect(self.export_pdf_file)
        
        export_btn_layout.addWidget(self.png_btn)
        export_btn_layout.addWidget(self.svg_btn)
        export_btn_layout.addWidget(self.pdf_btn)
        layout.addLayout(export_btn_layout)
        
        # Close Button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
    def load_qr_preview(self):
        """Generates and loads the QR code image preview inside the dialog."""
        try:
            # We pass the logo_path to make the preview render the same as the final PNG (with logo overlay)
            pil_img = generate_qr_image(self.qr_url, box_size=10, border=2)
            
            # Embed logo in the preview image if configured
            logo_path = self.business_data.get('logo_path')
            if logo_path and os.path.exists(logo_path):
                try:
                    logo = PILImage = QImage # just import locally to avoid conflicting with reportlab
                    from PIL import Image as PILImage
                    logo_img = PILImage.open(logo_path)
                    logo_size_pct = 0.20
                    qr_w, qr_h = pil_img.size
                    logo_w = int(qr_w * logo_size_pct)
                    logo_h = int(qr_h * logo_size_pct)
                    logo_img = logo_img.resize((logo_w, logo_h), PILImage.Resampling.LANCZOS)
                    pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)
                    if logo_img.mode in ('RGBA', 'LA'):
                        mask = logo_img.split()[-1]
                        pil_img.paste(logo_img, pos, mask)
                    else:
                        pil_img.paste(logo_img, pos)
                except Exception as logo_err:
                    logger.error(f"Failed to show logo in preview: {logo_err}")

            # Convert PIL image to QPixmap
            buffer = BytesIO()
            pil_img.save(buffer, format="PNG")
            qpixmap = QPixmap()
            qpixmap.loadFromData(buffer.getvalue(), "PNG")
            
            # Scaled for QLabel
            scaled_pixmap = qpixmap.scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Failed to generate QR preview: {e}")
            self.qr_image_label.setText("Error generating preview")
            self.qr_image_label.setStyleSheet("color: #ef4444; background-color: white; border-radius: 12px;")

    def export_png_file(self):
        """Saves the QR code as a PNG file."""
        default_name = f"qr_{self.business_data['name'].lower().replace(' ', '_')}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export QR as PNG", default_name, "PNG Images (*.png)"
        )
        if file_path:
            try:
                export_png(self.qr_url, file_path, self.business_data.get('logo_path'))
                QMessageBox.information(self, "Success", f"QR Code successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PNG: {e}")

    def export_svg_file(self):
        """Saves the QR code as an SVG file."""
        default_name = f"qr_{self.business_data['name'].lower().replace(' ', '_')}.svg"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export QR as SVG", default_name, "SVG Vector Images (*.svg)"
        )
        if file_path:
            try:
                export_svg(self.qr_url, file_path)
                QMessageBox.information(self, "Success", f"QR Code successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export SVG: {e}")

    def export_pdf_file(self):
        """Saves the QR code inside a print-ready PDF flyer."""
        default_name = f"flyer_{self.business_data['name'].lower().replace(' ', '_')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Print-Ready PDF Flyer", default_name, "PDF Documents (*.pdf)"
        )
        if file_path:
            try:
                export_pdf(
                    self.qr_url, 
                    file_path, 
                    self.business_data['name'], 
                    self.business_data.get('address', ''), 
                    self.business_data.get('logo_path')
                )
                QMessageBox.information(self, "Success", f"PDF Flyer successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PDF: {e}")
