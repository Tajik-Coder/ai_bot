"""
Configuration management for the Telegram AI Bot.
Uses pydantic for validation and environment variable parsing.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    """Immutable configuration class."""
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///telegram_bot.db"
    log_level: str = "INFO"
    max_log_size_mb: int = 10
    log_backup_count: int = 5
    ai_provider: str = "g4f"
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        return cls(
            bot_token=bot_token,
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            log_level=os.getenv("LOG_LEVEL", cls.log_level).upper(),
            max_log_size_mb=int(os.getenv("MAX_LOG_SIZE_MB", cls.max_log_size_mb)),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", cls.log_backup_count)),
            ai_provider=os.getenv("AI_PROVIDER", cls.ai_provider)
        )

# Global configuration instance
config = Config.load()