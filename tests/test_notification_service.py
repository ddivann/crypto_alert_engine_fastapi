"""
Integration tests for the Notification Service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from shared.schemas import AlertTriggeredMessage, AlertCondition


@pytest.mark.asyncio
async def test_telegram_message_formatting():
    """Test Telegram message formatting."""
    from services.notification_service.telegram_sender import TelegramSender
    
    sender = TelegramSender("test_token")
    
    alert_data = {
        "symbol": "BTCUSDT",
        "current_price": 45000.50,
        "condition": "above",
        "threshold": 44000.00,
        "message": "BTC price crossed threshold"
    }
    
    formatted = sender.format_alert_message(alert_data)
    
    assert "BTCUSDT" in formatted
    assert "$45,000.50" in formatted
    assert "ABOVE" in formatted
    assert "$44,000.00" in formatted


@pytest.mark.asyncio
async def test_notification_retry_logic():
    """Test notification retry logic on failure."""
    from services.notification_service.telegram_sender import TelegramSender
    
    sender = TelegramSender("test_token")
    sender.retry_config.max_attempts = 2  # Reduce for testing
    
    # Mock bot that fails
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
    sender.bot = mock_bot
    
    # Try to send notification
    success = await sender.send_notification(123, "Test message")
    
    # Should fail after retries
    assert success is False
    assert mock_bot.send_message.call_count == 2  # Should retry


@pytest.mark.asyncio
async def test_notification_success():
    """Test successful notification sending."""
    from services.notification_service.telegram_sender import TelegramSender
    
    sender = TelegramSender("test_token")
    
    # Mock bot that succeeds
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    sender.bot = mock_bot
    
    # Try to send notification
    success = await sender.send_notification(123, "Test message")
    
    # Should succeed
    assert success is True
    assert mock_bot.send_message.call_count == 1
