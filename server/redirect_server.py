import os
import base64
import logging
import uuid
import tempfile
from flask import Flask, redirect, render_template_string, abort, request, send_file, jsonify, after_this_request
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from models.business import (
    get_business_by_identifier, 
    update_expired_statuses, 
    add_business, 
    update_business, 
    delete_business, 
    get_business, 
    list_businesses, 
    get_settings,
    calculate_expiration_date
)
from utils.logger import get_logger
from utils.link_resolver import resolve_maps_url
from utils.qr_generator import generate_qr_image, export_pdf
from io import BytesIO

logger = get_logger("redirect_server")

# Disable default flask output logs to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask("QRRedirectServer")

# Create directories
IS_VERCEL = os.environ.get('VERCEL') or os.environ.get('NOW_REGION')
if IS_VERCEL:
    LOGOS_DIR = "/tmp/logos"
else:
    LOGOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logos")

os.makedirs(LOGOS_DIR, exist_ok=True)

# Auto-initialize database on Vercel
db_initialized = False
@app.before_request
def auto_init_db():
    global db_initialized
    if IS_VERCEL and not db_initialized:
        try:
            from database.connection import init_db
            init_db()
            db_initialized = True
            logger.info("SQLite database auto-initialized on Vercel.")
        except Exception as e:
            logger.error(f"Failed to auto-initialize database: {e}")

from flask import has_request_context

def get_dynamic_redirect_base_url():
    """Resolves the base URL to encode in the QR code, dynamically using the current request host if on Vercel or if using default localhost settings."""
    settings = get_settings()
    db_base_url = settings.get("redirect_base_url", "http://localhost:3000")
    
    if has_request_context():
        try:
            current_host = request.host_url.rstrip('/')
            # If running on Vercel, always use request.host_url (since SQLite is ephemeral)
            # If the settings value is default localhost, but the user is accessing via something else (like IP or live domain), use current host
            if IS_VERCEL or db_base_url == "http://localhost:3000" or "localhost" not in current_host:
                return current_host
        except Exception as e:
            logger.error(f"Error resolving dynamic base URL: {e}")
            
    return db_base_url


# Custom HTML Templates for clean, mobile-responsive layout
LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leave a Review - {{ business_name }}</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #f8fafc;
        }
        .card {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px 30px;
            width: 100%;
            max-width: 440px;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
        }
        .logo-container {
            width: 100px;
            height: 100px;
            margin: 0 auto 24px;
            border-radius: 50%;
            overflow: hidden;
            background: #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 3px solid #3b82f6;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
        }
        .logo {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .default-logo {
            font-size: 40px;
            font-weight: bold;
            color: #93c5fd;
        }
        h1 {
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }
        .address {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 28px;
            line-height: 1.4;
        }
        .rating-prompt {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 12px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .star-rating {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 30px;
        }
        .star {
            font-size: 48px;
            color: #cbd5e1;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
            -webkit-user-select: none;
        }
        .star:hover {
            transform: scale(1.25);
        }
        .btn {
            display: inline-block;
            width: 100%;
            padding: 16px 24px;
            background: rgba(255, 255, 255, 0.05);
            color: #94a3b8;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            border-radius: 14px;
            transition: all 0.2s ease;
            border: 1px solid rgba(255, 255, 255, 0.1);
            cursor: pointer;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }
        .compliance {
            font-size: 11px;
            color: #64748b;
            margin-top: 32px;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-container">
            {% if logo_base64 %}
                <img class="logo" src="data:image/png;base64,{{ logo_base64 }}" alt="{{ business_name }} Logo">
            {% else %}
                <div class="default-logo">{{ business_name[0] | upper }}</div>
            {% endif %}
        </div>
        <h1>{{ business_name }}</h1>
        {% if address %}
            <p class="address">{{ address }}</p>
        {% else %}
            <div style="height: 10px;"></div>
        {% endif %}
        
        <p class="rating-prompt">Tap a star to review:</p>
        <div class="star-rating">
            <span class="star" data-index="0">&#9733;</span>
            <span class="star" data-index="1">&#9733;</span>
            <span class="star" data-index="2">&#9733;</span>
            <span class="star" data-index="3">&#9733;</span>
            <span class="star" data-index="4">&#9733;</span>
        </div>
        
        <a href="{{ review_url }}" class="btn" target="_blank">Or open review page directly</a>
        
        <p class="compliance">
            Reviews must be submitted voluntarily. Tapping stars launches the Google Review portal, where you can write and submit your rating.
        </p>
    </div>

    <script>
        const stars = document.querySelectorAll('.star');
        const reviewUrl = "{{ review_url }}";
        let permanentHighlight = -1;

        stars.forEach((star, index) => {
            // Hover effect
            star.addEventListener('mouseover', () => {
                highlightStars(index);
            });
            star.addEventListener('mouseout', () => {
                resetStars();
            });

            // Tap/Click Action
            star.addEventListener('click', () => {
                highlightStars(index, true);
                
                // Open review link in new tab after selection animation
                setTimeout(() => {
                    window.open(reviewUrl, "_blank");
                }, 350);
            });
        });

        function highlightStars(index, isPermanent = false) {
            stars.forEach((s, idx) => {
                if (idx <= index) {
                    s.style.color = '#fbbf24'; // Gold color
                    s.style.textShadow = '0 0 15px rgba(251, 191, 36, 0.6)';
                } else {
                    s.style.color = '#cbd5e1'; // Slate gray
                    s.style.textShadow = 'none';
                }
            });
            if (isPermanent) {
                permanentHighlight = index;
            }
        }

        function resetStars() {
            if (permanentHighlight >= 0) {
                highlightStars(permanentHighlight);
            } else {
                stars.forEach(s => {
                    s.style.color = '#cbd5e1';
                    s.style.textShadow = 'none';
                });
            }
        }
    </script>
</body>
</html>
"""

EXPIRED_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscription Inactive - 5-Star QR</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background: #080d16;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(22, 28, 45, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(244, 63, 94, 0.2);
            border-radius: 24px;
            padding: 50px 30px;
            width: 100%;
            max-width: 440px;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .icon-container {
            width: 80px;
            height: 80px;
            margin: 0 auto 24px;
            border-radius: 50%;
            background: rgba(244, 63, 94, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #f43f5e;
            box-shadow: 0 0 15px rgba(244, 63, 94, 0.2);
        }
        .icon {
            font-size: 40px;
            color: #f43f5e;
            font-weight: bold;
        }
        h1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #ffffff;
        }
        p {
            font-size: 15px;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        .contact {
            font-size: 13px;
            color: #64748b;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-container">
            <div class="icon">!</div>
        </div>
        <h1>QR Code Expired</h1>
        <p>This QR code service is currently inactive. The deadline associated with this code has passed.</p>
        <p class="contact">Please contact the creator to extend the deadline.</p>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>5-Star QR Code Maker & Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #080d16;
            --bg-secondary: #0f1626;
            --card-bg: rgba(22, 28, 45, 0.5);
            --card-border: rgba(255, 255, 255, 0.06);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-blue-glow: rgba(59, 130, 246, 0.3);
            --accent-emerald: #10b981;
            --accent-emerald-glow: rgba(16, 185, 129, 0.3);
            --accent-rose: #f43f5e;
            --accent-rose-glow: rgba(244, 63, 94, 0.3);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Header Styling */
        header {
            background-color: rgba(15, 22, 38, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            padding: 15px 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 22px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .header-logo span {
            color: var(--accent-blue);
            text-shadow: 0 0 10px var(--accent-blue-glow);
        }

        .server-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-emerald);
            border: 1px solid rgba(16, 185, 129, 0.2);
            padding: 6px 14px;
            border-radius: 20px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-emerald);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-emerald);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.6; }
            50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px var(--accent-emerald); }
            100% { transform: scale(0.9); opacity: 0.6; }
        }

        /* Main Content Container */
        .container {
            max-width: 1300px;
            width: 100%;
            margin: 30px auto;
            padding: 0 20px;
            display: grid;
            grid-template-columns: 420px 1fr;
            gap: 30px;
            flex-grow: 1;
        }

        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
            }
        }

        /* Glass Cards */
        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 30px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
        }

        /* Creator Form panel */
        .creator-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 20px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        input[type="text"], select, input[type="datetime-local"] {
            width: 100%;
            background-color: rgba(8, 13, 22, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #ffffff;
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 14px;
            outline: none;
            transition: var(--transition);
        }

        input[type="text"]:focus, select:focus, input[type="datetime-local"]:focus {
            border-color: var(--accent-blue);
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.2);
        }

        .custom-exp-group {
            display: none;
            margin-top: 12px;
        }

        /* File Upload Styling */
        .file-upload-container {
            border: 2px dashed rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
            background: rgba(8, 13, 22, 0.3);
        }

        .file-upload-container:hover {
            border-color: var(--accent-blue);
            background: rgba(59, 130, 246, 0.03);
        }

        .file-upload-container input {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .upload-icon {
            font-size: 32px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .upload-text {
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .upload-text span {
            color: var(--accent-blue);
            font-weight: 600;
        }

        .file-selected-name {
            margin-top: 8px;
            font-size: 12px;
            color: var(--accent-emerald);
            font-weight: 600;
        }

        /* Generate Button */
        .submit-btn {
            width: 100%;
            background: linear-gradient(135deg, var(--accent-blue) 0%, #1d4ed8 100%);
            color: #ffffff;
            border: none;
            padding: 14px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
        }

        .submit-btn:active {
            transform: translateY(1px);
        }

        .submit-btn:disabled {
            background: #1e293b;
            color: #64748b;
            box-shadow: none;
            cursor: not-allowed;
        }

        /* Right Panel Directory */
        .directory-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 25px;
            gap: 20px;
        }

        .directory-title {
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
        }

        .search-container {
            display: flex;
            gap: 10px;
            width: 320px;
        }

        .search-container input {
            width: 100%;
            padding: 10px 16px;
        }

        /* Grid list of QR codes */
        .qr-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 20px;
            max-height: 80vh;
            overflow-y: auto;
            padding-right: 5px;
        }

        /* Custom Scrollbar for Grid */
        .qr-grid::-webkit-scrollbar {
            width: 6px;
        }
        .qr-grid::-webkit-scrollbar-track {
            background: transparent;
        }
        .qr-grid::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        .qr-grid::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .no-data {
            grid-column: 1 / -1;
            text-align: center;
            padding: 80px 20px;
            color: var(--text-secondary);
            font-size: 15px;
        }

        .no-data-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }

        /* QR Card UI */
        .qr-card {
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            transition: var(--transition);
        }

        .qr-card:hover {
            transform: translateY(-4px);
            border-color: rgba(59, 130, 246, 0.2);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.7);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }

        .biz-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            overflow: hidden;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid rgba(255, 255, 255, 0.1);
            font-weight: 800;
            font-size: 20px;
            color: var(--accent-blue);
            object-fit: cover;
            flex-shrink: 0;
        }

        .biz-info {
            flex-grow: 1;
            min-width: 0;
        }

        .biz-name {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .biz-date {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Status badges */
        .status-badge {
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status-active {
            background-color: rgba(16, 185, 129, 0.12);
            color: var(--accent-emerald);
            border: 1px solid rgba(16, 185, 129, 0.2);
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.05);
        }

        .status-expired {
            background-color: rgba(244, 63, 94, 0.12);
            color: var(--accent-rose);
            border: 1px solid rgba(244, 63, 94, 0.2);
            box-shadow: 0 0 10px rgba(244, 63, 94, 0.05);
        }

        /* Card body with QR Code Preview */
        .card-body {
            display: grid;
            grid-template-columns: 100px 1fr;
            gap: 15px;
            background: rgba(8, 13, 22, 0.3);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            align-items: center;
        }

        .qr-preview-container {
            width: 100px;
            height: 100px;
            background-color: white;
            border-radius: 8px;
            padding: 5px;
            cursor: pointer;
            transition: var(--transition);
        }

        .qr-preview-container:hover {
            transform: scale(1.05);
        }

        .qr-preview-container img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .qr-details {
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 0;
        }

        .detail-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .detail-label {
            font-size: 11px;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
        }

        .detail-value {
            font-size: 13px;
            color: #e2e8f0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Countdown display */
        .countdown-text {
            font-size: 13px;
            font-weight: 700;
            color: var(--accent-blue);
        }
        .countdown-text.expired-text {
            color: var(--accent-rose);
        }

        /* Card actions */
        .card-actions {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
            margin-top: auto;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 15px;
        }

        .btn-icon {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            color: var(--text-secondary);
            width: 34px;
            height: 34px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: var(--transition);
            font-size: 14px;
        }

        .btn-icon:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }

        .btn-icon.btn-delete:hover {
            background: rgba(244, 63, 94, 0.15);
            color: var(--accent-rose);
            border-color: rgba(244, 63, 94, 0.3);
        }

        .btn-icon.btn-edit:hover {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
            border-color: rgba(59, 130, 246, 0.3);
        }

        /* Dropdowns for downloads */
        .download-dropdown {
            position: relative;
            display: inline-block;
        }

        .dropdown-menu {
            display: none;
            position: absolute;
            bottom: 40px;
            right: 0;
            background-color: var(--bg-secondary);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.5);
            z-index: 10;
            min-width: 120px;
            overflow: hidden;
        }

        .dropdown-menu a {
            display: block;
            color: var(--text-secondary);
            padding: 8px 16px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: var(--transition);
        }

        .dropdown-menu a:hover {
            background-color: rgba(255, 255, 255, 0.05);
            color: #ffffff;
        }

        .download-dropdown:hover .dropdown-menu {
            display: block;
        }

        /* Modal popup styling */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background-color: var(--bg-secondary);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            width: 100%;
            max-width: 420px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
            position: relative;
            transform: scale(0.9);
            transition: var(--transition);
        }

        .modal.active .modal-content {
            transform: scale(1);
        }

        .modal-header {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 20px;
            color: #ffffff;
        }

        .modal-close {
            position: absolute;
            top: 20px;
            right: 20px;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
        }

        .modal-close:hover {
            color: #ffffff;
        }

        .modal-actions {
            display: flex;
            gap: 12px;
            margin-top: 25px;
            justify-content: flex-end;
        }

        .btn-cancel {
            background: transparent;
            border: 1px solid var(--card-border);
            color: var(--text-secondary);
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
        }

        .btn-cancel:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
        }

        .btn-save {
            background: var(--accent-blue);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
        }

        .btn-save:hover {
            background: #2563eb;
        }

        /* Large Zoom Image Preview */
        .zoom-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.9);
            z-index: 2000;
            align-items: center;
            justify-content: center;
            cursor: zoom-out;
        }
        .zoom-modal.active {
            display: flex;
        }
        .zoom-img {
            max-width: 450px;
            width: 100%;
            background: white;
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 0 30px rgba(0,0,0,0.5);
            transform: scale(0.9);
            transition: var(--transition);
        }
        .zoom-modal.active .zoom-img {
            transform: scale(1);
        }

        /* Toast Message notification */
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: var(--bg-secondary);
            border-left: 4px solid var(--accent-blue);
            border-radius: 8px;
            padding: 15px 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            transform: translateY(150px);
            opacity: 0;
            transition: var(--transition);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .toast.active {
            transform: translateY(0);
            opacity: 1;
        }

        .toast-icon {
            font-size: 18px;
        }

        .toast-text {
            font-size: 14px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-logo">
            <span>⭐</span> 5-Star QR Maker
        </div>
        <div class="server-status">
            <div class="status-dot"></div>
            Server Online (Port 3000)
        </div>
    </header>

    <div class="container">
        <!-- Generator Form Left Column -->
        <div class="glass-card">
            <div class="creator-title">
                ⚡ Create QR Code
            </div>
            
            <form id="create-form" onsubmit="handleCreate(event)">
                <div class="form-group">
                    <label for="google_maps_url">Google Maps Link *</label>
                    <input type="text" id="google_maps_url" name="google_maps_url" placeholder="Paste maps.app.goo.gl or search link..." required>
                </div>

                <div class="form-group">
                    <label for="name">Business Name (Optional)</label>
                    <input type="text" id="name" name="name" placeholder="Auto-fills from Google Maps link if blank">
                </div>

                <div class="form-group">
                    <label for="duration">QR Expiration Deadline *</label>
                    <select id="duration" name="duration" onchange="toggleCustomDuration(this.value)">
                        <option value="1 hour">1 Hour (For testing)</option>
                        <option value="1 day">1 Day</option>
                        <option value="1 week">1 Week</option>
                        <option value="1 month">1 Month</option>
                        <option value="12 months" selected>12 Months</option>
                        <option value="custom">Custom Date & Time</option>
                        <option value="No expiration">Lifetime (No expiration)</option>
                    </select>
                    
                    <div id="custom-exp-group" class="custom-exp-group">
                        <label for="custom_expiration" style="margin-top: 10px;">Select Expiration Date & Time</label>
                        <input type="datetime-local" id="custom_expiration" name="custom_expiration">
                    </div>
                </div>

                <div class="form-group">
                    <label>Overlay Business Logo (Optional)</label>
                    <div class="file-upload-container">
                        <input type="file" id="logo" name="logo" accept="image/*" onchange="handleFileSelected(this)">
                        <div class="upload-icon">📁</div>
                        <div class="upload-text">Drag & drop logo or <span>browse</span></div>
                        <div id="file-name" class="file-selected-name" style="display: none;"></div>
                    </div>
                </div>

                <button type="submit" id="submit-btn" class="submit-btn">
                    <span>⚡ Generate QR Code</span>
                </button>
            </form>
        </div>

        <!-- Manager Right Column -->
        <div class="glass-card" style="display: flex; flex-direction: column;">
            <div class="directory-header">
                <div class="directory-title">
                    QR Directory (<span id="total-qrs">0</span>)
                </div>
                <div class="search-container">
                    <input type="text" id="search-box" class="glass-input" placeholder="🔍 Search business name..." oninput="handleSearch(this.value)">
                </div>
            </div>

            <div id="qr-grid" class="qr-grid">
                <!-- Data dynamically loaded -->
                <div class="no-data">
                    <div class="no-data-icon">⭐</div>
                    <div>No QR codes generated yet. Use the generator on the left!</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal for Edit Expiration Deadline -->
    <div id="edit-modal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <div class="modal-header">📅 Edit QR Expiration Deadline</div>
            <input type="hidden" id="edit-id">
            <div class="form-group">
                <label for="edit_expiration">Select Expiration Date & Time</label>
                <input type="datetime-local" id="edit_expiration" required>
            </div>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="closeModal()">Cancel</button>
                <button class="btn-save" onclick="saveNewDeadline()">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Large Zoom Modal -->
    <div id="zoom-modal" class="zoom-modal" onclick="closeZoom()">
        <img id="zoom-img" class="zoom-img" src="" alt="Zoom QR">
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast">
        <span id="toast-icon" class="toast-icon">✓</span>
        <span id="toast-text" class="toast-text">Success message</span>
    </div>

    <script>
        let qrList = [];
        let searchTimeout = null;

        // On document load
        document.addEventListener('DOMContentLoaded', () => {
            loadQRList();
            
            // Start the countdown updates every second
            setInterval(updateCountdowns, 1000);
        });

        // Toggles custom expiration date picker visibility
        function toggleCustomDuration(value) {
            const group = document.getElementById('custom-exp-group');
            const picker = document.getElementById('custom_expiration');
            if (value === 'custom') {
                group.style.display = 'block';
                picker.required = true;
                // Default custom picker to tomorrow
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                tomorrow.setMinutes(tomorrow.getMinutes() - tomorrow.getTimezoneOffset());
                picker.value = tomorrow.toISOString().slice(0, 16);
            } else {
                group.style.display = 'none';
                picker.required = false;
            }
        }

        // Handles logo file selected text display
        function handleFileSelected(input) {
            const label = document.getElementById('file-name');
            if (input.files && input.files[0]) {
                label.textContent = "Selected: " + input.files[0].name;
                label.style.display = 'block';
            } else {
                label.style.display = 'none';
            }
        }

        // Toast Helper
        function showToast(text, isError = false) {
            const toast = document.getElementById('toast');
            const icon = document.getElementById('toast-icon');
            const message = document.getElementById('toast-text');
            
            message.textContent = text;
            if (isError) {
                toast.style.borderLeftColor = 'var(--accent-rose)';
                icon.textContent = '✗';
                icon.style.color = 'var(--accent-rose)';
            } else {
                toast.style.borderLeftColor = 'var(--accent-emerald)';
                icon.textContent = '✓';
                icon.style.color = 'var(--accent-emerald)';
            }
            
            toast.classList.add('active');
            setTimeout(() => {
                toast.classList.remove('active');
            }, 3000);
        }

        // Fetch businesses list
        async function loadQRList(searchQuery = '') {
            try {
                const response = await fetch(`/api/list?search=${encodeURIComponent(searchQuery)}`);
                const result = await response.json();
                if (result.success) {
                    qrList = result.businesses;
                    renderQRList();
                } else {
                    showToast("Failed to fetch list: " + result.error, true);
                }
            } catch (err) {
                showToast("Network error fetching grid.", true);
            }
        }

        // Render card UI
        function renderQRList() {
            const grid = document.getElementById('qr-grid');
            const totalCount = document.getElementById('total-qrs');
            
            totalCount.textContent = qrList.length;
            
            if (qrList.length === 0) {
                grid.innerHTML = `
                    <div class="no-data">
                        <div class="no-data-icon">⭐</div>
                        <div>No matching QR codes found.</div>
                    </div>
                `;
                return;
            }
            
            grid.innerHTML = '';
            qrList.forEach(biz => {
                const isExpired = biz.status !== 'Active';
                const firstLetter = biz.name ? biz.name.charAt(0).toUpperCase() : 'B';
                
                // Expiration display
                let expDisplay = biz.expiration_date ? biz.expiration_date : 'Lifetime';
                
                // Avatar display: server serving base64 logo if exists, else first-letter initials
                const avatarHTML = biz.logo_path 
                    ? `<img class="biz-avatar" src="/logo/${biz.id}" alt="${biz.name} Logo">`
                    : `<div class="biz-avatar">${firstLetter}</div>`;
                
                // Build Card element
                const card = document.createElement('div');
                card.className = 'glass-card qr-card';
                card.setAttribute('data-expiration', biz.expiration_date || '');
                card.setAttribute('data-id', biz.id);
                
                card.innerHTML = `
                    <div class="card-header">
                        ${avatarHTML}
                        <div class="biz-info">
                            <div class="biz-name" title="${biz.name}">${biz.name}</div>
                            <div class="biz-date">Created: ${biz.created_at ? biz.created_at.split(' ')[0] : 'N/A'}</div>
                        </div>
                        <span class="status-badge ${isExpired ? 'status-expired' : 'status-active'}">
                            ${biz.status}
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="qr-preview-container" title="Click to enlarge" onclick="openZoom('/qr/${biz.qr_identifier}')">
                            <img src="/qr/${biz.qr_identifier}" alt="QR code">
                        </div>
                        <div class="qr-details">
                            <div class="detail-item">
                                <span class="detail-label">Scanning Destination</span>
                                <span class="detail-value" title="Takes user to review dialog on maps.google.com">Google Maps Review Page</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Countdown</span>
                                <span class="countdown-text ${isExpired ? 'expired-text' : ''}">
                                    ${isExpired ? 'Expired' : 'Calculating...'}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="card-actions">
                        <button class="btn-icon btn-edit" title="Edit Expiration" onclick="openEditModal(${biz.id}, '${biz.expiration_date}')">📅</button>
                        <button class="btn-icon" title="Copy QR Link" onclick="copyQRLink('${biz.qr_identifier}')">🔗</button>
                        
                        <!-- Dropdown download -->
                        <div class="download-dropdown">
                            <button class="btn-icon" title="Download formats">💾</button>
                            <div class="dropdown-menu">
                                <a href="/download/png/${biz.qr_identifier}" download>Download PNG</a>
                                <a href="/download/svg/${biz.qr_identifier}" download>Download SVG</a>
                                <a href="/download/pdf/${biz.qr_identifier}" download>Download Flyer PDF</a>
                            </div>
                        </div>
                        
                        <button class="btn-icon btn-delete" title="Delete Profile" onclick="handleDelete(${biz.id}, '${biz.name}')">🗑</button>
                    </div>
                `;
                grid.appendChild(card);
            });
            
            // Run immediate countdown calculations
            updateCountdowns();
        }

        // Live countdowns calculation updates
        function updateCountdowns() {
            const cards = document.querySelectorAll('.qr-card[data-expiration]');
            cards.forEach(card => {
                const expStr = card.getAttribute('data-expiration');
                const countdownVal = card.querySelector('.countdown-text');
                const badge = card.querySelector('.status-badge');
                
                if (!expStr || expStr.trim() === '') {
                    countdownVal.textContent = "Lifetime (Never)";
                    countdownVal.classList.remove('expired-text');
                    if (badge) {
                        badge.className = "status-badge status-active";
                        badge.textContent = "Active";
                    }
                    return;
                }
                
                // Convert to Date. Replace space with 'T' for robust cross-browser ISO 8601 parsing
                const isoStr = expStr.replace(' ', 'T');
                const expDate = new Date(isoStr);
                const now = new Date();
                const diff = expDate - now;
                
                if (diff <= 0) {
                    countdownVal.textContent = "Expired";
                    countdownVal.classList.add('expired-text');
                    if (badge && badge.textContent.trim() === "Active") {
                        badge.className = "status-badge status-expired";
                        badge.textContent = "Expired";
                    }
                } else {
                    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                    
                    let timeStr = "";
                    if (days > 0) timeStr += `${days}d `;
                    if (days > 0 || hours > 0) timeStr += `${hours}h `;
                    timeStr += `${minutes}m ${seconds}s`;
                    
                    countdownVal.textContent = timeStr;
                    countdownVal.classList.remove('expired-text');
                    if (badge && badge.textContent.trim() === "Expired") {
                        badge.className = "status-badge status-active";
                        badge.textContent = "Active";
                    }
                }
            });
        }

        // Submits Create QR Form
        async function handleCreate(event) {
            event.preventDefault();
            
            const submitBtn = document.getElementById('submit-btn');
            submitBtn.disabled = true;
            submitBtn.querySelector('span').textContent = 'Generating QR...';
            
            const formData = new FormData(event.target);
            
            try {
                const response = await fetch('/api/create', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    showToast("QR Code successfully generated!");
                    event.target.reset();
                    document.getElementById('file-name').style.display = 'none';
                    document.getElementById('custom-exp-group').style.display = 'none';
                    loadQRList();
                } else {
                    showToast("Failed: " + result.error, true);
                }
            } catch (err) {
                showToast("Network error generating QR code.", true);
            } finally {
                submitBtn.disabled = false;
                submitBtn.querySelector('span').textContent = '⚡ Generate QR Code';
            }
        }

        // Handles Search box text updates
        function handleSearch(val) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadQRList(val);
            }, 300);
        }

        // Copy dynamic link to Clipboard
        function copyQRLink(qrIdentifier) {
            const link = `${window.location.protocol}//${window.location.host}/r/${qrIdentifier}`;
            navigator.clipboard.writeText(link).then(() => {
                showToast("Redirection link copied to clipboard!");
            }).catch(err => {
                showToast("Failed to copy link.", true);
            });
        }

        // Modal triggers
        function openEditModal(id, currentExpiration) {
            document.getElementById('edit-id').value = id;
            const picker = document.getElementById('edit_expiration');
            
            if (currentExpiration && currentExpiration.trim() !== '') {
                // Populate picker with current expiry. Convert YYYY-MM-DD HH:MM:SS to YYYY-MM-DDTHH:MM
                const datePart = currentExpiration.slice(0, 10);
                const timePart = currentExpiration.slice(11, 16);
                picker.value = `${datePart}T${timePart}`;
            } else {
                // default to tomorrow
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                tomorrow.setMinutes(tomorrow.getMinutes() - tomorrow.getTimezoneOffset());
                picker.value = tomorrow.toISOString().slice(0, 16);
            }
            
            document.getElementById('edit-modal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('edit-modal').classList.remove('active');
        }

        // Save Edited Deadline
        async function saveNewDeadline() {
            const id = document.getElementById('edit-id').value;
            const newDate = document.getElementById('edit_expiration').value;
            
            if (!newDate) {
                alert("Please select a date and time!");
                return;
            }
            
            try {
                const response = await fetch('/api/edit-deadline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: parseInt(id), expiration_date: newDate })
                });
                const result = await response.json();
                if (result.success) {
                    showToast("Deadline successfully updated!");
                    closeModal();
                    loadQRList();
                } else {
                    showToast("Failed to update: " + result.error, true);
                }
            } catch (err) {
                showToast("Network error updating deadline.", true);
            }
        }

        // Delete Business Profile
        async function handleDelete(id, name) {
            if (!confirm(`Are you sure you want to delete the QR code profile for '${name}'?\\nThis will break any printed QR codes!`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                });
                const result = await response.json();
                if (result.success) {
                    showToast(`Profile for '${name}' deleted.`);
                    loadQRList();
                } else {
                    showToast("Failed to delete: " + result.error, true);
                }
            } catch (err) {
                showToast("Network error deleting profile.", true);
            }
        }

        // Zoom QR preview modal triggers
        function openZoom(src) {
            const modal = document.getElementById('zoom-modal');
            const img = document.getElementById('zoom-img');
            img.src = src;
            modal.classList.add('active');
        }

        function closeZoom() {
            document.getElementById('zoom-modal').classList.remove('active');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(DASHBOARD_HTML)

@app.route('/r/<qr_identifier>')
def redirect_to_review(qr_identifier):
    """Checks business status and redirects to review URL directly or displays expiration notice."""
    # Synchronize expired statuses first
    update_expired_statuses()
    
    business = get_business_by_identifier(qr_identifier)
    if not business:
        logger.warning(f"Scan attempt on non-existent identifier: {qr_identifier}")
        abort(404)
        
    logger.info(f"QR Scanned for Business: {business['name']} (ID: {business['id']}, Status: {business['status']})")
    
    # Check subscription status
    if business['status'] != 'Active':
        return render_template_string(EXPIRED_PAGE_HTML), 403
        
    # Redirect directly to Google Review URL
    return redirect(business['review_url'])

@app.route('/api/list')
def api_list():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'All').strip()
    
    # Sync statuses first
    update_expired_statuses()
    
    businesses = list_businesses(search_query=search, status_filter=status)
    return jsonify({"success": True, "businesses": businesses})

@app.route('/api/create', methods=['POST'])
def api_create():
    name = request.form.get('name', '').strip()
    maps_url = request.form.get('google_maps_url', '').strip()
    duration = request.form.get('duration', '12 months')
    custom_expiration = request.form.get('custom_expiration', '').strip()
    
    if not maps_url:
        return jsonify({"success": False, "error": "Google Maps link is required."})
        
    # Resolve the Google Maps Link (with fallback if resolution fails)
    resolved_url = maps_url
    extracted_name = ""
    try:
        res_url, ext_name, error_msg = resolve_maps_url(maps_url)
        if not error_msg and res_url:
            resolved_url = res_url
            extracted_name = ext_name
    except Exception as e:
        logger.error(f"Error resolving link: {str(e)}")
        
    # Use extracted name if name is empty
    if not name:
        name = extracted_name if extracted_name else "Google Maps Business"
        
    # Calculate expiration date
    expiration_date = ""
    if duration == "custom":
        if custom_expiration:
            # custom_expiration is in 'YYYY-MM-DDTHH:MM' format from datetime-local input
            try:
                dt = datetime.strptime(custom_expiration, "%Y-%m-%dT%H:%M")
                expiration_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid custom expiration date format: {str(e)}"})
        else:
            return jsonify({"success": False, "error": "Custom expiration date and time is required."})
    elif duration == "1 hour":
        expiration_date = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif duration == "1 day":
        expiration_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif duration == "1 week":
        expiration_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    elif duration != "No expiration":
        # Standard durations: 1 month, 3 months, 6 months, 12 months
        expiration_date = calculate_expiration_date(duration)
        
    # Check if expired initially
    status = "Active"
    if expiration_date:
        # get current datetime: YYYY-MM-DD HH:MM:SS
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if expiration_date < now_str:
            status = "Expired"
            
    # Process logo upload
    logo_path = ""
    if 'logo' in request.files:
        logo_file = request.files['logo']
        if logo_file and logo_file.filename:
            ext = os.path.splitext(logo_file.filename)[1]
            filename = f"{uuid.uuid4()}{ext}"
            path = os.path.join(LOGOS_DIR, filename)
            logo_file.save(path)
            logo_path = path
            
    try:
        business_id = add_business(
            name=name,
            review_url=resolved_url,
            address="",
            contact_info="",
            logo_path=logo_path,
            qr_mode="Dynamic",
            subscription_duration=duration,
            expiration_date=expiration_date,
            status=status
        )
        return jsonify({"success": True, "business_id": business_id})
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to save profile: {str(e)}"})

@app.route('/api/edit-deadline', methods=['POST'])
def api_edit_deadline():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON request."})
        
    business_id = data.get('id')
    new_expiration = data.get('expiration_date', '').strip()
    
    if not business_id or not new_expiration:
        return jsonify({"success": False, "error": "ID and new expiration date are required."})
        
    # parse new_expiration: it could be 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM:SS'
    expiration_date = ""
    try:
        if 'T' in new_expiration:
            dt = datetime.strptime(new_expiration, "%Y-%m-%dT%H:%M")
        else:
            dt = datetime.strptime(new_expiration, "%Y-%m-%d %H:%M:%S")
        expiration_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid expiration date format: {str(e)}"})
        
    # Update business
    business = get_business(business_id)
    if not business:
        return jsonify({"success": False, "error": "Business profile not found."})
        
    status = "Active"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if expiration_date < now_str:
        status = "Expired"
        
    try:
        update_business(
            business_id=business_id,
            name=business['name'],
            review_url=business['review_url'],
            address=business.get('address', ''),
            contact_info=business.get('contact_info', ''),
            logo_path=business.get('logo_path', ''),
            qr_mode=business.get('qr_mode', 'Dynamic'),
            subscription_duration="Custom date",
            expiration_date=expiration_date,
            status=status
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"})

@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({"success": False, "error": "ID is required."})
        
    business_id = data['id']
    try:
        # Optionally remove the logo file if it exists
        business = get_business(business_id)
        if business and business.get('logo_path'):
            logo_path = business['logo_path']
            if os.path.exists(logo_path):
                try:
                    os.remove(logo_path)
                except Exception as logo_err:
                    logger.error(f"Failed to delete logo file: {logo_err}")
                    
        delete_business(business_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"})

@app.route('/qr/<qr_identifier>')
def serve_qr_code(qr_identifier):
    business = get_business_by_identifier(qr_identifier)
    if not business:
        abort(404)
        
    if business.get('qr_mode') == 'Direct':
        qr_url = business['review_url']
    else:
        redirect_base_url = get_dynamic_redirect_base_url()
        qr_url = f"{redirect_base_url.rstrip('/')}/r/{business['qr_identifier']}"
    
    try:
        # Box size 10 is perfect for web display
        img = generate_qr_image(qr_url, box_size=10, border=2)
        
        # Overlay logo if configured
        logo_path = business.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            from PIL import Image as PILImage
            logo_img = PILImage.open(logo_path)
            logo_size_pct = 0.20
            qr_w, qr_h = img.size
            logo_w = int(qr_w * logo_size_pct)
            logo_h = int(qr_h * logo_size_pct)
            logo_img = logo_img.resize((logo_w, logo_h), PILImage.Resampling.LANCZOS)
            pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)
            if logo_img.mode in ('RGBA', 'LA'):
                mask = logo_img.split()[-1]
                img.paste(logo_img, pos, mask)
            else:
                img.paste(logo_img, pos)
                
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return send_file(buffer, mimetype="image/png")
    except Exception as e:
        logger.error(f"Error serving QR code: {e}")
        abort(500)

@app.route('/logo/<int:business_id>')
def serve_logo(business_id):
    business = get_business(business_id)
    if business and business.get('logo_path') and os.path.exists(business['logo_path']):
        # Determine content type dynamically
        ext = os.path.splitext(business['logo_path'])[1].lower()
        mimetype = "image/png"
        if ext in ['.jpg', '.jpeg']:
            mimetype = "image/jpeg"
        elif ext == '.gif':
            mimetype = "image/gif"
        elif ext == '.bmp':
            mimetype = "image/bmp"
            
        return send_file(business['logo_path'], mimetype=mimetype)
    abort(404)

@app.route('/download/png/<qr_identifier>')
def download_png(qr_identifier):
    business = get_business_by_identifier(qr_identifier)
    if not business:
        abort(404)
    if business.get('qr_mode') == 'Direct':
        qr_url = business['review_url']
    else:
        redirect_base_url = get_dynamic_redirect_base_url()
        qr_url = f"{redirect_base_url.rstrip('/')}/r/{business['qr_identifier']}"
    
    try:
        # Generate high resolution image
        img = generate_qr_image(qr_url, box_size=15, border=4)
        
        logo_path = business.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            from PIL import Image as PILImage
            logo_img = PILImage.open(logo_path)
            logo_size_pct = 0.20
            qr_w, qr_h = img.size
            logo_w = int(qr_w * logo_size_pct)
            logo_h = int(qr_h * logo_size_pct)
            logo_img = logo_img.resize((logo_w, logo_h), PILImage.Resampling.LANCZOS)
            pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)
            if logo_img.mode in ('RGBA', 'LA'):
                mask = logo_img.split()[-1]
                img.paste(logo_img, pos, mask)
            else:
                img.paste(logo_img, pos)
                
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        filename = f"qr_{business['name'].lower().replace(' ', '_')}.png"
        return send_file(buffer, mimetype="image/png", as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Failed to download PNG: {e}")
        abort(500)

@app.route('/download/svg/<qr_identifier>')
def download_svg(qr_identifier):
    business = get_business_by_identifier(qr_identifier)
    if not business:
        abort(404)
    if business.get('qr_mode') == 'Direct':
        qr_url = business['review_url']
    else:
        redirect_base_url = get_dynamic_redirect_base_url()
        qr_url = f"{redirect_base_url.rstrip('/')}/r/{business['qr_identifier']}"
    
    try:
        import qrcode.image.svg
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(qr_url, image_factory=factory)
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        filename = f"qr_{business['name'].lower().replace(' ', '_')}.svg"
        return send_file(buffer, mimetype="image/svg+xml", as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Failed to download SVG: {e}")
        abort(500)

@app.route('/download/pdf/<qr_identifier>')
def download_pdf(qr_identifier):
    business = get_business_by_identifier(qr_identifier)
    if not business:
        abort(404)
    if business.get('qr_mode') == 'Direct':
        qr_url = business['review_url']
    else:
        redirect_base_url = get_dynamic_redirect_base_url()
        qr_url = f"{redirect_base_url.rstrip('/')}/r/{business['qr_identifier']}"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = tmp.name
        
    try:
        export_pdf(
            qr_url,
            tmp_path,
            business['name'],
            business.get('address', ''),
            business.get('logo_path')
        )
        
        @after_this_request
        def remove_file(response):
            try:
                os.remove(tmp_path)
            except Exception as e:
                logger.error(f"Failed to remove temp PDF: {e}")
            return response
            
        filename = f"flyer_{business['name'].lower().replace(' ', '_')}.pdf"
        return send_file(tmp_path, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Failed to download PDF: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        abort(500)

try:
    from PySide6.QtCore import QThread, Signal
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

if PYSIDE_AVAILABLE:
    class RedirectServerThread(QThread):
        """QThread running the Flask redirect server background process."""
        server_error = Signal(str)
        
        def __init__(self, host="0.0.0.0", port=3000):
            super().__init__()
            self.host = host
            self.port = port
            self.daemon = True # Daemon thread kills itself when main thread dies

        def run(self):
            try:
                logger.info(f"Starting Local Redirect Server on {self.host}:{self.port}...")
                # Run Flask Werkzeug server in this thread
                app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                logger.error(f"Failed to run local redirect server: {e}")
                self.server_error.emit(str(e))
else:
    class RedirectServerThread:
        pass
