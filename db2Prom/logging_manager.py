import structlog
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_path: str, log_level: str):
    """
    Set up structured logging with rotating file handlers.
    """
    # Create log directory if it doesn't exist
    os.makedirs(log_path, exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Main log handler (rotating file handler)
    log_file = os.path.join(log_path, "db2prom.log")
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Error log handler (rotating file handler)
    error_log_file = os.path.join(log_path, "db2prom.err")
    error_handler = RotatingFileHandler(error_log_file, maxBytes=10*1024*1024, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Console handler for real-time debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)