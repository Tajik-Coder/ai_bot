"""
Main application entry point with graceful shutdown handling.
"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.database.connection import Database
from app.handlers.router import setup_routers
from app.utils.logger import get_logger
from config import config

logger = get_logger(__name__)

class Application:
    """Main application class managing bot lifecycle."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.database: Optional[Database] = None
        self._shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize application components."""
        logger.info("Starting Telegram AI Bot...")
        
        # Initialize database
        self.database = Database()
        await self.database.connect()
        logger.info("Database connected")
        
        # Initialize bot with HTML parse mode
        self.bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Initialize dispatcher
        self.dp = Dispatcher()
        
        # Setup dependency injection context
        from app.services.ai_service import AIService
        ai_service = AIService()
        
        # Inject dependencies to dispatcher
        self.dp.workflow_data.update({
            'database': self.database,
            'ai_service': ai_service
        })
        
        # Setup routers
        setup_routers(self.dp)
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("Application startup completed")
    
    async def shutdown(self):
        """Cleanup application resources."""
        logger.info("Shutting down application...")
        
        # Close bot session
        if self.bot:
            await self.bot.session.close()
            logger.info("Bot session closed")
        
        # Close database connection
        if self.database:
            await self.database.disconnect()
            logger.info("Database disconnected")
        
        self._shutdown_event.set()
        logger.info("Application shutdown completed")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()
    
    async def run(self):
        """Main application run loop."""
        await self.startup()
        
        try:
            # Start polling
            logger.info("Starting bot polling...")
            await self.dp.start_polling(
                self.bot,
                handle_signals=False  # We handle signals manually
            )
        except asyncio.CancelledError:
            logger.info("Polling cancelled")
        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)
        finally:
            await self.shutdown()

async def main():
    """Main async entry point."""
    app = Application()
    
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Application terminated")

if __name__ == "__main__":
    asyncio.run(main())