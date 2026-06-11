import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    """Sets up the global logging configuration."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    
    # Use writeable temp logs folder on Vercel
    if os.environ.get('VERCEL') or os.environ.get('NOW_REGION'):
        log_dir = "/tmp/logs"
        
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Clear root handlers if any
    logging.root.handlers = []

    # Formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler (Rolling, max 5MB, keep 3 backup files)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

def get_logger(name):
    """Returns a logger instance for the specified module name."""
    return logging.getLogger(name)
