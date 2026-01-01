"""
Router setup and command handlers for the Telegram bot.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.database.repository import UserRepository, MessageRepository
from app.services.ai_service import AIService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# State machine for conversation
class ConversationStates(StatesGroup):
    waiting_for_ai_response = State()

def setup_routers(dp) -> None:
    """Setup all routers and handlers."""
    router = Router()
    
    # Register command handlers
    router.message.register(start_handler, CommandStart())
    router.message.register(help_handler, Command("help"))
    router.message.register(clear_handler, Command("clear"))
    router.message.register(stats_handler, Command("stats"))
    
    # Register message handler (text messages)
    router.message.register(message_handler, F.text)
    
    # Register error handler
    router.errors.register(error_handler)
    
    dp.include_router(router)

async def start_handler(message: Message, database) -> None:
    """Handle /start command."""
    user_repo = UserRepository(database)
    
    # Get or create user
    user = await user_repo.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )
    
    welcome_text = (
        "🤖 <b>Welcome to AI Assistant Bot!</b>\n\n"
        "I'm here to help you with any questions you have.\n"
        "Just send me a message and I'll respond!\n\n"
        "Available commands:\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history\n"
        "/stats - Show your usage statistics\n\n"
        "Let's start our conversation!"
    )
    
    await message.answer(welcome_text)

async def help_handler(message: Message) -> None:
    """Handle /help command."""
    help_text = (
        "📚 <b>Help & Commands</b>\n\n"
        "<b>Available Commands:</b>\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/clear - Clear your conversation history\n"
        "/stats - Show your usage statistics\n\n"
        "<b>How to use:</b>\n"
        "• Just type your message and I'll respond\n"
        "• I remember our conversation history\n"
        "• Use /clear to start a new conversation\n\n"
        "Need help? Contact the administrator!"
    )
    
    await message.answer(help_text)

async def clear_handler(message: Message, database) -> None:
    """Handle /clear command."""
    user_repo = UserRepository(database)
    message_repo = MessageRepository(database)
    
    # Get user
    user = await user_repo.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )
    
    # Clear conversation
    await message_repo.clear_conversation(user['id'])
    
    await message.answer(
        "🗑️ <b>Conversation cleared!</b>\n\n"
        "I've deleted all our previous messages. "
        "We can start a fresh conversation!"
    )

async def stats_handler(message: Message, database) -> None:
    """Handle /stats command."""
    user_repo = UserRepository(database)
    message_repo = MessageRepository(database)
    
    # Get user
    user = await user_repo.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )
    
    # Get message count
    message_count = await message_repo.get_message_count(user['id'])
    
    stats_text = (
        "📊 <b>Your Statistics</b>\n\n"
        f"<b>User ID:</b> {user['id']}\n"
        f"<b>Username:</b> @{user['username'] or 'Not set'}\n"
        f"<b>Joined:</b> {user['created_at']}\n"
        f"<b>Total Messages:</b> {message_count}\n\n"
        "Keep chatting to increase your stats!"
    )
    
    await message.answer(stats_text)

async def message_handler(
    message: Message, 
    database, 
    ai_service: AIService,
    state: FSMContext
) -> None:
    """Handle regular text messages."""
    # Ignore empty messages
    if not message.text or message.text.strip() == "":
        return
    
    user_repo = UserRepository(database)
    message_repo = MessageRepository(database)
    
    # Get or create user
    user = await user_repo.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )
    
    # Save user message to database
    await message_repo.create_message(
        user_id=user['id'],
        role='user',
        content=message.text
    )
    
    # Get conversation history
    history = await message_repo.get_conversation_history(user['id'], limit=10)
    
    # Format history for AI
    formatted_history = []
    for msg in reversed(history):  # Oldest first
        formatted_history.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # Send typing action
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )
    
    try:
        # Get AI response
        ai_response = await ai_service.generate_response(
            message=message.text,
            history=formatted_history
        )
        
        # Save AI response to database
        await message_repo.create_message(
            user_id=user['id'],
            role='assistant',
            content=ai_response
        )
        
        # Send response
        await message.answer(ai_response)
        
    except Exception as e:
        logger.error(f"AI service error: {e}", exc_info=True)
        await message.answer(
            "⚠️ <b>Sorry, I encountered an error processing your request.</b>\n\n"
            "Please try again in a moment. "
            "If the problem persists, contact the administrator."
        )

async def error_handler(update, exception) -> None:
    """Global error handler."""
    logger.error(f"Update {update} caused error: {exception}", exc_info=True)
    return True