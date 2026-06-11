# QR Review Manager

QR Review Manager is a desktop application written in Python using PySide6 (Qt6) and SQLite. It provides multi-business profile management, automated subscription expiration handling, high-quality QR code exporting, and a local redirection server.

---

## ⚠️ The QR Expiration Tradeoff (Static vs. Dynamic)

When printing a QR code on physical materials (flyers, menus, tables), **the data encoded in that QR code cannot change**. 

1. **Static (Direct Mode)**: If a QR code is generated pointing directly to `https://maps.google.com/...`, the scan will always load Google Maps directly. It is completely offline and serverless, but **it can never be expired, disabled, or redirected** because you do not control the destination domain.
2. **Dynamic (Redirect Mode)**: To enable expiration dates and subscription deactivation, the QR code must point to a redirect URL that you control (e.g., `http://<your-server>/r/<id>`). When scanned:
   - The phone hits the redirect server.
   - The server queries the SQLite database.
   - If active, the server redirects (HTTP 302) the user to Google.
   - If expired, the server displays a mobile-friendly page: *"Subscription expired. Contact your provider."*
   
**This Application Supports Both Modes:**
When adding/editing a business profile, you can choose **Dynamic** (recommened for subscription control) or **Direct** (static link directly to Google).

---

## 📱 Local Network Testing (Mobile Setup)

To test dynamic QR codes and deactivations from your phone completely offline:
1. Ensure your PC and smartphone are connected to the **same local Wi-Fi network**.
2. Open the app, navigate to **Settings**, and locate your **Local Network IP** (e.g. `192.168.1.50`).
3. Set the **Redirect Server Base URL** in settings to: `http://<your-local-ip>:5000` (e.g., `http://192.168.1.50:5000`) and click **Save Settings**.
4. Create a business, select **Dynamic** mode, and choose a subscription length (or set "Custom date" to yesterday to test expiration).
5. Open the QR preview inside the app and scan it with your smartphone camera.
   - **Active profile**: Opens a sleek branding page showing the business logo, name, and a "Leave a Google Review" button.
   - **Expired profile**: Displays the red warning page: *"Subscription Expired. Contact your provider."*

*Note: For production deployment, you would host the Flask redirect handler on a public cloud server (e.g. Render, AWS, Heroku) and enter the public URL in the settings panel.*

---

## 🛠️ Project Folder Structure

```
qr_review_manager/
│
├── main.py                  # Main entry point (initializes DB & starts UI)
├── requirements.txt         # Project package dependencies
│
├── database/
│   └── connection.py        # SQLite connection setup, schema init, backup & restore
│
├── models/
│   └── business.py          # Business CRUD queries, stats calculation, date parser
│
├── server/
│   └── redirect_server.py   # Flask server in a QThread serving redirects & landing pages
│
├── ui/
│   ├── main_window.py       # Sidebar navigation layout, thread orchestrator
│   ├── dashboard.py         # Summary metrics, soon-to-expire warnings, CSV report
│   ├── business_list.py     # Business search grid with add, edit, delete buttons
│   ├── business_dialog.py   # Form validator dialog with date pickers & logo browse
│   ├── qr_viewer.py         # Visual QR code previewer & exporter
│   └── styles.py            # Custom QSS premium dark mode stylesheet
│
└── utils/
    ├── logger.py            # Configures console and rolling file logs (logs/app.log)
    └── qr_generator.py      # QR code compilation (PNG with logo overlay, SVG, PDF Flyer)
```

---

## 🚀 Installation & Setup

1. **Clone or copy** this directory to your target location.
2. Open your terminal (PowerShell or Command Prompt) and navigate to the project directory:
   ```bash
   cd "c:\Users\jaatp\OneDrive\Desktop\5-star QR"
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   - **Windows PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows Command Prompt**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
5. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Run the application:
   ```bash
   python main.py
   ```

---

## 📦 Building a Standalone Windows Executable (.exe)

You can package this application into a single standalone `.exe` or a folder distribution using **PyInstaller**.

### Option A: Folder Distribution (Recommended)
This creates a folder containing the `.exe` alongside its necessary libraries. It starts up much faster than a single-file build because files don't need to unpack to a temp directory.

```bash
pyinstaller --noconfirm --onedir --windowed --name "QRReviewManager" main.py
```
After completion, open the compiled folder at: `dist/QRReviewManager/QRReviewManager.exe`.

### Option B: Single File Executable
If you prefer a single `.exe` file for easy distribution:

```bash
pyinstaller --noconfirm --onefile --windowed --name "QRReviewManager" main.py
```
Your compiled file will be located at: `dist/QRReviewManager.exe`.

*Note: Data files (`data/qr_manager.db`) and log directories (`logs/app.log`) are generated dynamically by Python at runtime inside the folder containing the executable, keeping user data safe and externalized.*
