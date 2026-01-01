"""
AI Service using g4f for text generation.
"""
import g4f
from typing import List, Dict, Optional
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.utils.logger import get_logger
from config import config

logger = get_logger(__name__)

@dataclass
class AIResponse:
    """Structured AI response."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None

class AIService:
    """Service for AI text generation using g4f."""
    
    def __init__(self):
        self.model = "gpt-3.5-turbo"  # Default model
        self.max_tokens = 2048
        self.temperature = 0.7
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Available models (fallback order)
        self.available_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
        ]
        
        logger.info(f"AI Service initialized with provider: {config.ai_provider}")
    
    async def generate_response(
        self, 
        message: str, 
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate AI response for a message with conversation history.
        
        Args:
            message: User's message
            history: Conversation history in OpenAI format
            
        Returns:
            AI response as string
        """
        try:
            # Prepare messages list
            messages = []
            
            # Add system message
            system_prompt = """You are a helpful AI assistant in a Telegram bot. 
            Be concise, friendly, and helpful. 
            Keep responses reasonably short for mobile users."""
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history
            if history:
                messages.extend(history)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Generate response using g4f
            response = await self._call_g4f(messages)
            
            # Clean up response
            response = response.strip()
            
            logger.debug(f"Generated response: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}", exc_info=True)
            return (
                "I apologize, but I'm having trouble processing your request right now. "
                "Please try again in a moment. If the problem persists, "
                "the administrator has been notified."
            )
    
    async def _call_g4f(self, messages: List[Dict[str, str]]) -> str:
        """
        Call g4f API with retry logic and fallback models.
        
        Args:
            messages: List of messages in OpenAI format
            
        Returns:
            Generated text response
        """
        last_exception = None
        
        # Try different models as fallback
        for model in self.available_models:
            try:
                logger.debug(f"Trying model: {model}")
                
                # Run g4f in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    self._executor,
                    lambda: g4f.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        timeout=30  # 30 second timeout
                    )
                )
                
                if response and isinstance(response, str):
                    logger.info(f"Successfully generated response using {model}")
                    return response
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Model {model} failed: {str(e)[:100]}")
                continue
        
        # If all models failed
        error_msg = f"All AI models failed. Last error: {last_exception}"
        logger.error(error_msg)
        raise Exception(error_msg) from last_exception
    
    async def test_connection(self) -> bool:
        """Test AI service connection."""
        try:
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'Hello' if you're working."}
            ]
            
            response = await self._call_g4f(test_messages)
            return "hello" in response.lower()
            
        except Exception as e:
            logger.error(f"AI service test failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        self._executor.shutdown(wait=False)
        logger.info("AI Service cleanup completed")