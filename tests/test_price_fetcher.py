"""
Integration tests for the Price Fetcher service.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from shared.schemas import PriceTickMessage
from services.price_fetcher.publisher import RedisPublisher


@pytest.mark.asyncio
async def test_redis_publisher():
    """Test Redis publisher publishes messages correctly."""
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock()
    
    publisher = RedisPublisher(mock_redis)
    
    # Create test message
    message = PriceTickMessage(
        symbol="BTCUSDT",
        exchange="binance",
        price=45000.0,
        volume=100.0
    )
    
    # Publish message
    await publisher.publish_price_tick(message)
    
    # Verify xadd was called
    assert mock_redis.xadd.called
    assert publisher.get_message_count() == 1


@pytest.mark.asyncio
async def test_websocket_client_message_handling():
    """Test WebSocket client handles messages correctly."""
    from services.price_fetcher.websocket_client import BinanceWebSocketClient
    
    # Mock publisher
    mock_publisher = AsyncMock()
    mock_publisher.publish_price_tick = AsyncMock()
    
    client = BinanceWebSocketClient(mock_publisher)
    
    # Test message from Binance
    test_message = '''
    {
        "stream": "btcusdt@trade",
        "data": {
            "e": "trade",
            "E": 1234567890000,
            "s": "BTCUSDT",
            "t": 12345,
            "p": "45000.50",
            "q": "0.001",
            "T": 1234567890000
        }
    }
    '''
    
    await client._handle_message(test_message)
    
    # Verify publisher was called
    assert mock_publisher.publish_price_tick.called
    call_args = mock_publisher.publish_price_tick.call_args[0][0]
    assert call_args.symbol == "BTCUSDT"
    assert call_args.price == 45000.50
    assert call_args.exchange == "binance"
