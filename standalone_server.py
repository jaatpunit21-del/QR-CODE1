import sys
import os

# Ensure the root project directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_db
from models.business import update_expired_statuses
from server.redirect_server import app

def main():
    print("=" * 60)
    print("         STANDALONE QR REVIEW REDIRECT SERVER")
    print("=" * 60)
    
    # 1. Initialize database and schemas if not present
    print("[*] Initializing SQLite database...")
    init_db()
    
    # 2. Sync expirations against current system time
    print("[*] Syncing subscription expiration statuses...")
    update_expired_statuses()
    
    # 3. Start Werkzeug development server
    print("\n[*] Starting Local Redirect Server...")
    print("    - Local URL:   http://localhost:3000")
    print("    - Network URL: http://0.0.0.0:3000 (Allows mobile testing on same Wi-Fi)")
    print("\n    Press Ctrl+C to stop the server.")
    print("=" * 60)
    
    # Run the Flask app directly
    app.run(host="0.0.0.0", port=3000, debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
