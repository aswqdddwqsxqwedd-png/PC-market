"""Structured logging configuration."""
import logging
import sys
import os
import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, TimeStamper, add_log_level, StackInfoRenderer
from structlog.contextvars import merge_contextvars


def setup_logging(debug: bool = False) -> None:
    """
    Configure structured logging with JSON output.
    
    Args:
        debug: Enable debug logging level
    """
    # IMPORTANT: Configure database loggers FIRST, before any imports
    # This prevents "executing..." and "operation..." messages from aiosqlite
    
    # Disable SQLAlchemy echo mode via environment variable
    os.environ.setdefault("SQLALCHEMY_SILENCE_UBER_WARNING", "1")
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
        force=True,  # Override any existing configuration
    )
    
    # CRITICAL: Disable aiosqlite DEBUG logging FIRST
    # This is the source of "executing..." and "operation..." messages
    aiosqlite_logger = logging.getLogger("aiosqlite")
    aiosqlite_logger.setLevel(logging.ERROR)
    aiosqlite_logger.propagate = False
    aiosqlite_logger.handlers = []
    aiosqlite_logger.addHandler(logging.NullHandler())
    
    # Reduce SQLAlchemy and database driver logging verbosity
    # Set SQLAlchemy engine logging to ERROR to completely silence SQL query spam
    sqlalchemy_loggers = [
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
        "sqlalchemy",
    ]
    
    for logger_name in sqlalchemy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        logger.handlers = []
        logger.addHandler(logging.NullHandler())
    
    # Disable any other database-related loggers
    sqlite_logger = logging.getLogger("sqlite3")
    sqlite_logger.setLevel(logging.ERROR)
    sqlite_logger.propagate = False
    sqlite_logger.handlers = []
    sqlite_logger.addHandler(logging.NullHandler())
    
    # Configure structlog
    processors = [
        merge_contextvars,  # Merge context variables
        add_log_level,      # Add log level
        StackInfoRenderer(),  # Add stack info
        TimeStamper(fmt="iso"),  # ISO 8601 timestamp
    ]
    
    # Use JSON renderer for production, pretty for development
    if debug:
        from structlog.dev import ConsoleRenderer
        processors.append(ConsoleRenderer())
    else:
        processors.append(JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)

