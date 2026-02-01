"""
Common data schemas for inter-service communication.
All messages use JSON format with versioning.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages in the system."""
    PRICE_TICK = "price.tick"
    ALERT_TRIGGERED = "alert.triggered"


class PriceTickMessage(BaseModel):
    """Message published by Price Fetcher service."""
    version: str = Field(default="1.0", description="Schema version")
    message_type: MessageType = Field(default=MessageType.PRICE_TICK)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    exchange: str = Field(..., description="Exchange name (e.g., binance, bybit)")
    price: float = Field(..., gt=0, description="Current price")
    volume: Optional[float] = Field(None, ge=0, description="Trading volume")
    
    class Config:
        json_schema_extra = {
            "example": {
                "version": "1.0",
                "message_type": "price.tick",
                "timestamp": "2024-01-01T12:00:00Z",
                "symbol": "BTCUSDT",
                "exchange": "binance",
                "price": 45000.50,
                "volume": 123.45
            }
        }


class AlertCondition(str, Enum):
    """Alert condition types."""
    ABOVE = "above"
    BELOW = "below"
    PERCENT_CHANGE = "percent_change"


class AlertTriggeredMessage(BaseModel):
    """Message published by Alert Manager service."""
    version: str = Field(default="1.0", description="Schema version")
    message_type: MessageType = Field(default=MessageType.ALERT_TRIGGERED)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    alert_id: int = Field(..., description="Alert rule ID")
    user_id: int = Field(..., description="User ID")
    symbol: str = Field(..., description="Trading pair symbol")
    condition: AlertCondition = Field(..., description="Condition that was met")
    threshold: float = Field(..., description="Threshold value")
    current_price: float = Field(..., gt=0, description="Current price that triggered the alert")
    message: str = Field(..., description="Human-readable alert message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "version": "1.0",
                "message_type": "alert.triggered",
                "timestamp": "2024-01-01T12:00:00Z",
                "alert_id": 123,
                "user_id": 456,
                "symbol": "BTCUSDT",
                "condition": "above",
                "threshold": 45000.0,
                "current_price": 45001.0,
                "message": "BTC/USDT price ($45,001.00) is now above your threshold of $45,000.00"
            }
        }
