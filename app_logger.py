import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure python standard logging
LOG_FILE = "app_activity.log"

logger = logging.getLogger("GoldAlgo")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File Handler
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream / Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# In-memory buffer for Web UI Log Feed
MEMORY_LOGS: List[Dict[str, Any]] = []
MAX_MEMORY_LOGS = 200

def log_event(level: str, category: str, message: str, details: Dict[str, Any] = None):
    """
    Logs activity to file, console, and in-memory UI buffer.
    Categories: 'POLLING', 'SIGNAL', 'ORDER', 'BOOKING', 'SYSTEM', 'RISK'
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{category}] {message}"

    if level.upper() == "ERROR":
        logger.error(formatted_msg)
    elif level.upper() == "WARNING":
        logger.warning(formatted_msg)
    else:
        logger.info(formatted_msg)

    log_entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "category": category.upper(),
        "message": message,
        "details": details or {}
    }

    MEMORY_LOGS.append(log_entry)
    if len(MEMORY_LOGS) > MAX_MEMORY_LOGS:
        MEMORY_LOGS.pop(0)

    return log_entry

def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    return list(reversed(MEMORY_LOGS[-limit:]))
