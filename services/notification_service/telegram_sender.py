"""
Telegram notification sender using aiogram.
Sends alert messages to users via Telegram bot.
"""
import asyncio
from typing import Dict, Optional
from aiogram import Bot
from aiogram.enums import ParseMode

from shared.utils import setup_logging, RetryConfig


logger = setup_logging()


class TelegramSender:
    """Sends notifications via Telegram bot."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot: Optional[Bot] = None
        self.retry_config = RetryConfig(max_attempts=3, initial_delay=1.0)
        # In production, this would be fetched from a database
        # For MVP, we use a simple dict mapping user_id to telegram chat_id
        self._user_chat_mapping: Dict[int, int] = {}
    
    async def start(self):
        """Initialize the bot."""
        self.bot = Bot(token=self.bot_token)
        logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the bot."""
        if self.bot:
            await self.bot.session.close()
            logger.info("Telegram bot stopped")
    
    def register_user(self, user_id: int, chat_id: int):
        """
        Register mapping between internal user_id and Telegram chat_id.
        In production, this would be stored in a database.
        """
        self._user_chat_mapping[user_id] = chat_id
        logger.info(f"Registered user {user_id} with chat {chat_id}")
    
    async def send_notification(self, user_id: int, message: str) -> bool:
        """
        Send notification to a user via Telegram.
        
        Args:
            user_id: Internal user ID
            message: Message text to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.error("Bot not initialized")
            return False
        
        # Get Telegram chat_id for user
        chat_id = self._user_chat_mapping.get(user_id)
        if not chat_id:
            logger.warning(f"No Telegram chat_id found for user {user_id}")
            # For MVP, we'll use user_id as chat_id
            # In production, this should be properly registered
            chat_id = user_id
        
        # Retry logic with exponential backoff
        for attempt in range(self.retry_config.max_attempts):
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Sent notification to user {user_id}")
                return True
            
            except Exception as e:
                logger.error(f"Error sending notification (attempt {attempt + 1}): {e}")
                
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self.retry_config.get_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to send notification after {self.retry_config.max_attempts} attempts")
                    return False
        
        return False
    
    def format_alert_message(self, alert_data: dict) -> str:
        """
        Format alert data into a nice Telegram message.
        
        Args:
            alert_data: Alert information dictionary
            
        Returns:
            Formatted HTML message
        """
        symbol = alert_data.get("symbol", "")
        current_price = alert_data.get("current_price", 0)
        condition = alert_data.get("condition", "")
        threshold = alert_data.get("threshold", 0)
        message = alert_data.get("message", "")
        
        formatted = f"""
🚨 <b>Price Alert Triggered!</b>

<b>Symbol:</b> {symbol}
<b>Current Price:</b> ${current_price:,.2f}
<b>Condition:</b> {condition.upper()}
<b>Threshold:</b> ${threshold:,.2f}

{message}
"""
        return formatted.strip()
