"""
Shared utility functions and classes.
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


def now_utc() -> datetime:
    """Get current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def setup_logging() -> logging.Logger:
    """
    Set up structured logging for the application.
    Returns a configured logger instance.
    """
    from shared.config import get_settings
    settings = get_settings()
    
    logger = logging.getLogger(settings.service_name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": now_utc().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


def parse_message_data(message_data: dict, key: str = "data") -> str:
    """
    Parse message data from Redis, handling both bytes and string formats.
    
    Args:
        message_data: Message data dict from Redis
        key: Key to extract from message_data
        
    Returns:
        Parsed data as string
    """
    data = message_data.get(key.encode() if isinstance(list(message_data.keys())[0], bytes) else key)
    return data.decode() if isinstance(data, bytes) else data
