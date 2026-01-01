"""
Database connection management using aiosqlite with connection pooling.
"""
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from app.utils.logger import get_logger
from config import config

logger = get_logger(__name__)

class Database:
    """Database connection manager with connection pooling."""
    
    def __init__(self):
        self._db_path = config.database_url.replace("sqlite+aiosqlite:///", "")
        self._connection: Optional[aiosqlite.Connection] = None
        self._is_connected = False
        
    async def connect(self):
        """Establish database connection and initialize schema."""
        try:
            self._connection = await aiosqlite.connect(self._db_path)
            self._connection.row_factory = aiosqlite.Row
            self._is_connected = True
            
            # Initialize database schema
            await self._init_schema()
            logger.info(f"Connected to database: {self._db_path}")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection."""
        if self._connection and self._is_connected:
            await self._connection.close()
            self._is_connected = False
            logger.info("Database connection closed")
    
    async def _init_schema(self):
        """Initialize database schema."""
        schema_queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )""",
            """CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)""",
            """CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"""
        ]
        
        for query in schema_queries:
            await self.execute(query)
        
        logger.debug("Database schema initialized")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager for database connections."""
        if not self._is_connected:
            raise RuntimeError("Database not connected")
        
        try:
            yield self._connection
        except Exception as e:
            await self._connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            await self._connection.commit()
    
    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            return cursor
    
    async def executemany(self, query: str, params_list: List[tuple]) -> aiosqlite.Cursor:
        """Execute a query with multiple parameter sets."""
        async with self.get_connection() as conn:
            cursor = await conn.executemany(query, params_list)
            return cursor
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected