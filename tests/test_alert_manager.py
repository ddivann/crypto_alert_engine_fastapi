"""
Integration tests for the Alert Manager service.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from shared.schemas import PriceTickMessage, AlertCondition
from services.alert_manager.models import AlertRule, AlertConditionEnum


@pytest.mark.asyncio
async def test_alert_condition_above():
    """Test alert triggers when price goes above threshold."""
    from services.alert_manager.alert_checker import AlertChecker
    
    # Mock session maker and Redis
    mock_session_maker = MagicMock()
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock()
    
    checker = AlertChecker(mock_session_maker, mock_redis)
    
    # Create mock alert and session
    alert = AlertRule(
        id=1,
        user_id=123,
        symbol="BTCUSDT",
        exchange="binance",
        condition=AlertConditionEnum.ABOVE,
        threshold=44000.0,
        is_active=True
    )
    
    mock_session = AsyncMock()
    
    # Test price above threshold
    price_tick = PriceTickMessage(
        symbol="BTCUSDT",
        exchange="binance",
        price=45000.0,
        volume=100.0
    )
    
    should_trigger = await checker._should_trigger(alert, price_tick, mock_session)
    assert should_trigger is True


@pytest.mark.asyncio
async def test_alert_condition_below():
    """Test alert triggers when price goes below threshold."""
    from services.alert_manager.alert_checker import AlertChecker
    
    # Mock session maker and Redis
    mock_session_maker = MagicMock()
    mock_redis = AsyncMock()
    
    checker = AlertChecker(mock_session_maker, mock_redis)
    
    # Create mock alert
    alert = AlertRule(
        id=1,
        user_id=123,
        symbol="BTCUSDT",
        exchange="binance",
        condition=AlertConditionEnum.BELOW,
        threshold=46000.0,
        is_active=True
    )
    
    mock_session = AsyncMock()
    
    # Test price below threshold
    price_tick = PriceTickMessage(
        symbol="BTCUSDT",
        exchange="binance",
        price=45000.0,
        volume=100.0
    )
    
    should_trigger = await checker._should_trigger(alert, price_tick, mock_session)
    assert should_trigger is True


@pytest.mark.asyncio
async def test_alert_throttling():
    """Test that alerts are throttled correctly."""
    from services.alert_manager.alert_checker import AlertChecker
    from datetime import timedelta
    
    mock_session_maker = MagicMock()
    mock_redis = AsyncMock()
    
    checker = AlertChecker(mock_session_maker, mock_redis)
    
    # Create alert that was recently triggered
    alert = AlertRule(
        id=1,
        user_id=123,
        symbol="BTCUSDT",
        exchange="binance",
        condition=AlertConditionEnum.ABOVE,
        threshold=44000.0,
        is_active=True,
        last_triggered_at=datetime.utcnow() - timedelta(minutes=30)  # 30 min ago
    )
    
    mock_session = AsyncMock()
    
    price_tick = PriceTickMessage(
        symbol="BTCUSDT",
        exchange="binance",
        price=45000.0,
        volume=100.0
    )
    
    # Should not trigger due to throttling
    should_trigger = await checker._should_trigger(alert, price_tick, mock_session)
    assert should_trigger is False
