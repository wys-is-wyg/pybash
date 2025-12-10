"""
Centralized error logging for AI News Tracker.

Automatically catches and logs all unhandled exceptions without requiring
changes to individual scripts. Errors are written to a single errors.log file.
"""

import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from app.config import settings


# Error log file path
ERROR_LOG_FILE = settings.DATA_DIR / "errors.log"


def log_error(error_type, error_value, traceback_obj, context=None):
    """
    Log an error to errors.log file.
    
    Args:
        error_type: Exception type
        error_value: Exception value/message
        traceback_obj: Traceback object
        context: Optional context string (e.g., script name, function name)
    """
    try:
        # Ensure data directory exists
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Format error message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_name = error_type.__name__ if error_type else "UnknownError"
        error_msg = str(error_value) if error_value else "No error message"
        
        # Format traceback
        if traceback_obj:
            tb_lines = traceback.format_tb(traceback_obj)
            tb_text = "".join(tb_lines)
        else:
            tb_text = "No traceback available"
        
        # Build log entry
        log_entry = f"""
{'='*80}
[{timestamp}] ERROR: {error_name}
{'='*80}
Context: {context or 'Unhandled exception'}
Error: {error_msg}
Traceback:
{tb_text}
"""
        
        # Append to error log file
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            f.write("\n")
        
    except Exception:
        # If error logging itself fails, write to stderr as fallback
        print(f"[ERROR LOGGER FAILED] {error_type.__name__}: {error_value}", file=sys.stderr)


def exception_hook(error_type, error_value, traceback_obj):
    """
    Global exception handler that catches all unhandled exceptions.
    
    This is set as sys.excepthook to catch exceptions that aren't caught
    by try/except blocks.
    """
    # Get context from traceback (script name, line number)
    context = None
    if traceback_obj:
        try:
            frame = traceback_obj.tb_frame
            filename = Path(frame.f_code.co_filename).name
            line_no = traceback_obj.tb_lineno
            func_name = frame.f_code.co_name
            context = f"{filename}:{line_no} in {func_name}"
        except Exception:
            pass
    
    # Log the error
    log_error(error_type, error_value, traceback_obj, context)
    
    # Call default exception handler to still show error in console
    sys.__excepthook__(error_type, error_value, traceback_obj)


def log_exception(error, context=None):
    """
    Manually log an exception (for use in try/except blocks).
    
    Usage:
        try:
            # some code
        except Exception as e:
            log_exception(e, context="function_name")
    
    Args:
        error: Exception object
        context: Optional context string
    """
    error_type = type(error)
    error_value = error
    traceback_obj = error.__traceback__
    log_error(error_type, error_value, traceback_obj, context)


def cleanup_old_errors(days=7):
    """
    Remove error log entries older than specified days.
    
    Args:
        days: Number of days to keep (default: 7)
    """
    if not ERROR_LOG_FILE.exists():
        return
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Read all lines
        with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filter out old entries
        new_lines = []
        skip_entry = False
        
        for line in lines:
            # Check if this is a timestamp line
            if line.startswith('[') and '] ERROR:' in line:
                # Extract date from timestamp [YYYY-MM-DD HH:MM:SS]
                try:
                    date_str = line[1:11]  # Extract YYYY-MM-DD
                    if date_str < cutoff_str:
                        skip_entry = True
                        continue
                    else:
                        skip_entry = False
                except Exception:
                    pass
            
            if not skip_entry:
                new_lines.append(line)
        
        # Write back filtered lines
        with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
    except Exception:
        # If cleanup fails, just continue (don't break the app)
        pass


def initialize_error_logging():
    """
    Initialize global error logging.
    
    Call this once at application startup (e.g., in main.py or __init__.py).
    Sets up sys.excepthook to catch all unhandled exceptions.
    """
    # Set global exception handler
    sys.excepthook = exception_hook
    
    # Cleanup old errors on startup
    cleanup_old_errors(days=7)


# Auto-initialize when module is imported
# This ensures error logging works even if initialize_error_logging() isn't called
initialize_error_logging()

