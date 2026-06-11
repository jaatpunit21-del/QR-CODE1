import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from utils.logger import setup_logger, get_logger
from database.connection import init_db
from ui.main_window import MainWindow

# Initialize the rolling file logging system
setup_logger()
logger = get_logger("main")

def main():
    logger.info("Initializing QR Review Manager desktop application...")
    
    try:
        # Initialize the database and tables
        init_db()
    except Exception as db_err:
        logger.critical(f"Fatal database initialization error: {db_err}")
        print(f"Database error:\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Create Qt App
        app = QApplication(sys.argv)
        app.setApplicationName("QR Review Manager")
        app.setApplicationDisplayName("QR Review Manager")
        
        # Build main GUI
        window = MainWindow()
        window.show()
        
        # Execute Application event loop
        sys.exit(app.exec())
    except Exception as gui_err:
        logger.critical(f"Fatal GUI initialization error: {gui_err}")
        # Show alert to user if crash occurs during startup
        error_msg = f"A fatal error occurred on startup:\n\n{gui_err}\n\nCheck logs/app.log for details."
        
        # If QApplication is already running, show dialog box
        if QApplication.instance():
            QMessageBox.critical(None, "Application Startup Error", error_msg)
        else:
            print(error_msg, file=sys.stderr)
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
