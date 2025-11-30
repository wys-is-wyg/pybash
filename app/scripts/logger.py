"""
Logging configuration for AI News Tracker.

Sets up console and file logging handlers with configurable log levels.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import settings


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up and configure a logger instance.
    
    Args:
        name: Logger name (typically __name__ of calling module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set log level from environment or settings
    log_level = os.getenv("LOG_LEVEL", settings.LOG_LEVEL)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter(
        settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    settings.ensure_directories_exist()
    log_file = settings.get_log_file_path("app.log")
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.LOG_FILE_MAX_BYTES,
        backupCount=settings.LOG_FILE_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Create default logger instance
logger = setup_logger("ai_news_tracker")

