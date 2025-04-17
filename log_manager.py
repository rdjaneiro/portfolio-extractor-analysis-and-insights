import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure application logging"""
    # Configure logger
    logger = logging.getLogger("dashCoachAI_app")
    logger.setLevel(logging.DEBUG)

    # Configure root logger first to capture all logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Set specific loggers to higher levels to reduce noise
    logging.getLogger('watchdog').setLevel(logging.WARNING)  # Filter out watchdog DEBUG messages
    logging.getLogger('watchdog.observers').setLevel(logging.WARNING)  # Filter out watchdog observers
    logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)  # Filter out inotify buffer
    logging.getLogger('pandas').setLevel(logging.WARNING)  # Filter out pandas DEBUG messages

    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    if root_logger.handlers:
        root_logger.handlers.clear()

    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)  # Create logs directory if it doesn't exist

    # Add file handler to root logger only
    file_handler = RotatingFileHandler(
        "logs/dashCoachAI_app.log",
        maxBytes=1024*1024,
        backupCount=3
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Add console handler to root logger only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # Setup specific handler for httpcore logs
    setup_httpcore_logging()

    # Setup specific handler for OpenAI logs
    setup_openai_logging()

    # Allow propagation for module loggers to root logger
    # This way module names will be preserved in logs via the %(name)s in formatter
    # but we won't get duplicates since we're only adding handlers to the root logger
    logger.propagate = True  # Allow propagation to root logger with module name preserved

    # Log a test message to verify configuration
    logger.info(" +++++++++++++++++++++++++++ Logger initialized successfully +++++++++++++++++++++++++++")
    root_logger.info(" +++++++++++++++++++++++++++ Root logger initialized successfully +++++++++++++++++++++++++++")

    return logger

def setup_httpcore_logging():
    """Configure httpcore logging to a separate file"""
    http_logger = logging.getLogger('httpcore')
    http_logger.setLevel(logging.DEBUG)

    # Prevent httpcore logs from propagating to the root logger
    http_logger.propagate = False

    # Clear existing handlers if any
    if http_logger.handlers:
        http_logger.handlers.clear()

    # Create a rotating file handler for httpcore logs
    http_file_handler = RotatingFileHandler(
        "logs/dashCoachAI_http.log",
        maxBytes=1024*1024,
        backupCount=2
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    http_file_handler.setFormatter(formatter)
    http_file_handler.setLevel(logging.DEBUG)
    http_logger.addHandler(http_file_handler)

    http_logger.info("HTTP logger initialized successfully")

def setup_openai_logging():
    """Configure OpenAI logging to a separate file"""
    openai_logger = logging.getLogger('openai')
    openai_logger.setLevel(logging.DEBUG)

    # Prevent OpenAI logs from propagating to the root logger
    openai_logger.propagate = False

    # Clear existing handlers if any
    if openai_logger.handlers:
        openai_logger.handlers.clear()

    # Create a rotating file handler for OpenAI logs
    openai_file_handler = RotatingFileHandler(
        "logs/dashCoachAI_openai.log",
        maxBytes=1024*1024,
        backupCount=2
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    openai_file_handler.setFormatter(formatter)
    openai_file_handler.setLevel(logging.DEBUG)
    openai_logger.addHandler(openai_file_handler)

    openai_logger.info("OpenAI logger initialized successfully")

# Create a global logger instance
logger = setup_logging()

# Function to get a module-specific logger
def get_logger(name):
    """Get a logger for a specific module"""
    module_logger = logging.getLogger(name)
    module_logger.propagate = True  # Allow propagation to root logger
    return module_logger