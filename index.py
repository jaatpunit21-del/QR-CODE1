import sys
import os

# Ensure the root project directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Expose the Flask application
from server.redirect_server import app
