import os
import qrcode
import qrcode.image.svg
from io import BytesIO
from PIL import Image as PILImage
from utils.logger import get_logger

# ReportLab imports for professional PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logger = get_logger("qr_generator")

def generate_qr_image(url, box_size=10, border=4):
    """Generates a raw PIL Image for the QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction for custom logo overlays
        box_size=box_size,
        border=border
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert('RGB')

def export_png(url, file_path, logo_path=None):
    """Generates and saves a high-quality PNG QR Code, optionally overlaying a logo in the center."""
    try:
        img = generate_qr_image(url, box_size=15, border=4)
        
        if logo_path and os.path.exists(logo_path):
            try:
                # Load and prepare logo
                logo = PILImage.open(logo_path)
                logo_size_pct = 0.20 # Max 20% of QR code size
                
                # Calculate size
                qr_width, qr_height = img.size
                logo_width = int(qr_width * logo_size_pct)
                logo_height = int(qr_height * logo_size_pct)
                
                # Resize logo maintaining aspect ratio (or pad if needed, simple resize with LANCZOS here)
                logo = logo.resize((logo_width, logo_height), PILImage.Resampling.LANCZOS)
                
                # Calculate center position
                pos = ((qr_width - logo_width) // 2, (qr_height - logo_height) // 2)
                
                # Paste logo onto QR (handle transparency if present)
                if logo.mode in ('RGBA', 'LA'):
                    mask = logo.split()[-1]
                    img.paste(logo, pos, mask)
                else:
                    img.paste(logo, pos)
                    
                logger.info("Embedded business logo in the PNG QR code.")
            except Exception as logo_err:
                logger.error(f"Failed to embed logo in QR code: {logo_err}. Saving clean QR code instead.")
        
        img.save(file_path, "PNG")
        logger.info(f"Saved PNG QR to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting PNG QR: {e}")
        raise e

def export_svg(url, file_path):
    """Generates and saves a vector SVG QR Code."""
    try:
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(url, image_factory=factory)
        img.save(file_path)
        logger.info(f"Saved SVG QR to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting SVG QR: {e}")
        raise e

def export_pdf(url, file_path, business_name, address="", logo_path=None):
    """Generates a professional print-ready letter-size PDF flyer containing the QR Code and instructions."""
    try:
        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Define Custom Typography Styles
        title_style = ParagraphStyle(
            name='FlyerTitle',
            fontName='Helvetica-Bold',
            fontSize=32,
            leading=38,
            textColor=colors.HexColor('#1E293B'), # Slate 800
            alignment=1, # Centered
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            name='FlyerSubtitle',
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#2563EB'), # Blue 600
            alignment=1, # Centered
            spaceAfter=30
        )
        
        body_style = ParagraphStyle(
            name='FlyerBody',
            fontName='Helvetica',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#475569'), # Slate 600
            alignment=1,
            spaceAfter=20
        )
        
        footer_style = ParagraphStyle(
            name='FlyerFooter',
            fontName='Helvetica-Oblique',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#94A3B8'), # Slate 400
            alignment=1,
            spaceBefore=30
        )
        
        # 1. Add Business Name and Subtitle
        story.append(Paragraph(business_name, title_style))
        story.append(Paragraph("Review us on Google!", subtitle_style))
        story.append(Paragraph("Your feedback helps us grow. Please scan the QR code below and tell us about your experience.", body_style))
        
        # 2. Generate temporary QR code image for embedding in PDF
        temp_qr_path = file_path + ".temp_qr.png"
        export_png(url, temp_qr_path, logo_path)
        
        # Load temporary image into flowable
        qr_flowable = RLImage(temp_qr_path, width=3.5*inch, height=3.5*inch)
        story.append(qr_flowable)
        
        # 3. Add address or contact info if available
        if address:
            address_style = ParagraphStyle(
                name='FlyerAddress',
                fontName='Helvetica',
                fontSize=12,
                leading=14,
                textColor=colors.HexColor('#334155'),
                alignment=1,
                spaceBefore=15
            )
            story.append(Paragraph(f"Location: {address}", address_style))
            
        story.append(Paragraph("Thank you for your support!", footer_style))
        
        # Build Document
        doc.build(story)
        
        # Clean up temporary QR file
        if os.path.exists(temp_qr_path):
            os.remove(temp_qr_path)
            
        logger.info(f"Saved PDF Flyer to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting PDF QR: {e}")
        # Make sure cleanup runs
        temp_qr_path = file_path + ".temp_qr.png"
        if os.path.exists(temp_qr_path):
            os.remove(temp_qr_path)
        raise e
