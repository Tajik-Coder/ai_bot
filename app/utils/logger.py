"""
Structured logging setup for production.
"""
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import config

class CustomFormatter(logging.Formatter):
    """Custom log formatter with colors and structured format."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, use_color: bool = True):
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')
        self.use_color = use_color
    
    def format(self, record):
        """Format log record with optional colors."""
        formatted = super().format(record)
        
        if self.use_color and record.levelname in self.COLORS:
            formatted = (f"{self.COLORS[record.levelname]}{formatted}"
                        f"{self.COLORS['RESET']}")
        
        return formatted

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 10,
    backup_count: int = 5
) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level
        log_file: Path to log file (optional)
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(CustomFormatter(use_color=True))
    root_logger.addHandler(console_handler)
    
    # File handler if log file specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("g4f").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# Initialize logging on module import
setup_logging(
    log_level=config.log_level,
    log_file="logs/telegram_bot.log",
    max_size_mb=config.max_log_size_mb,
    backup_count=config.log_backup_count
)