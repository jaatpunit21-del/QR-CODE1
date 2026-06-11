import os
import sqlite3
import shutil
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("database")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "qr_manager.db")

# Detect Vercel environment to use writeable temp folder
IS_VERCEL = os.environ.get('VERCEL') or os.environ.get('NOW_REGION')
if IS_VERCEL:
    DB_PATH = "/tmp/qr_manager.db"

def get_db_path():
    """Returns the database file path."""
    return DB_PATH

def get_connection():
    """Returns a sqlite3 connection with WAL mode enabled (on local PC) and Row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    # Enable WAL mode for local concurrent access, but disable on Vercel
    if not IS_VERCEL:
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
    logger.info("Initializing SQLite database...")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create businesses table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            review_url TEXT NOT NULL,
            address TEXT,
            contact_info TEXT,
            logo_path TEXT,
            qr_identifier TEXT UNIQUE NOT NULL,
            subscription_duration TEXT,
            expiration_date TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            qr_mode TEXT NOT NULL DEFAULT 'Dynamic',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)

        # Set default settings
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('redirect_base_url', 'http://localhost:3000')")
        cursor.execute("UPDATE settings SET value = 'http://localhost:3000' WHERE key = 'redirect_base_url'")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('expiring_soon_days', '30')")

        conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()

def backup_database(dest_dir):
    """Backs up the SQLite database to the specified folder with a timestamped name."""
    try:
        os.makedirs(dest_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"qr_manager_backup_{timestamp}.db"
        dest_path = os.path.join(dest_dir, backup_filename)

        # To perform a safe hot backup of a WAL database, use the backup API
        # but for simple offline/local operations, standard shutil is fine if we lock or open direct
        src_conn = sqlite3.connect(DB_PATH)
        dest_conn = sqlite3.connect(dest_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()

        logger.info(f"Database backed up to {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        raise e

def restore_database(backup_path):
    """Restores the database from a backup file."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found at {backup_path}")

    try:
        # Close connection details and copy
        os.makedirs(DB_DIR, exist_ok=True)
        # Use SQLite backup API to restore safely
        dest_conn = sqlite3.connect(DB_PATH)
        src_conn = sqlite3.connect(backup_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()

        logger.info(f"Database restored from {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore database: {e}")
        raise e
