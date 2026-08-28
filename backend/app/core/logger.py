"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/core/logger.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Centralized logging facility with structured formatting, dual output
              handlers (stdout stream and rotating persistent file log), and
              consistent timestamping across all asynchronous components.
================================================================================
"""
import logging
import sys
from pathlib import Path

# Resolve logs directory path and guarantee directory existence
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Standard logging formats
FMT = "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"


# -----------------------------------------------------------------------------
# Structured Logger Setup Function
# -----------------------------------------------------------------------------
def setup_logger(name: str) -> logging.Logger:
    """
    Creates or retrieves a named logger instance configured with:
      - Console StreamHandler (Level: INFO)
      - FileHandler writing to logs/rag_system.log (Level: DEBUG)
    
    Args:
        name (str): The module or component name for logger identification.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    log = logging.getLogger(name)
    
    # Return immediately if handler is already attached to avoid duplicate log lines
    if log.handlers:
        return log
        
    log.setLevel(logging.DEBUG)

    # Console Handler: Formats INFO level and above to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(FMT, DATEFMT))

    # File Handler: Formats detailed DEBUG logs to persistent file
    file_handler = logging.FileHandler(LOG_DIR / "rag_system.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FMT, DATEFMT))

    # Register handlers
    log.addHandler(console_handler)
    log.addHandler(file_handler)
    
    return log
