"""
Repository pattern for database operations.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.database.connection import Database
from app.utils.logger import get_logger

logger = get_logger(__name__)

class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_or_create_user(self, telegram_id: int, username: Optional[str] = None) -> Dict[str, Any]:
        """Get existing user or create a new one."""
        # Try to get existing user
        user = await self.db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        if user:
            logger.debug(f"User found: {telegram_id}")
            return user
        
        # Create new user
        await self.db.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username)
        )
        
        # Get the created user
        user = await self.db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        logger.info(f"New user created: {telegram_id} ({username})")
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by internal ID."""
        return await self.db.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
    
    async def update_username(self, telegram_id: int, username: str) -> bool:
        """Update user's username."""
        result = await self.db.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id)
        )
        return result.rowcount > 0

class MessageRepository:
    """Repository for message operations."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_message(self, user_id: int, role: str, content: str) -> Dict[str, Any]:
        """Create a new message."""
        await self.db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        
        # Get the created message
        message = await self.db.fetch_one(
            "SELECT * FROM messages WHERE id = last_insert_rowid()"
        )
        
        logger.debug(f"Message created for user {user_id}: {role}")
        return message
    
    async def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        return await self.db.fetch_all(
            """
            SELECT role, content, created_at 
            FROM messages 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
    
    async def get_message_count(self, user_id: int) -> int:
        """Get total message count for a user."""
        result = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM messages WHERE user_id = ?",
            (user_id,)
        )
        return result['count'] if result else 0
    
    async def clear_conversation(self, user_id: int) -> bool:
        """Clear conversation history for a user."""
        result = await self.db.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (user_id,)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Conversation cleared for user {user_id}")
        return deleted