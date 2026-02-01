"""
Redis publisher for price tick events.
Publishes messages to Redis Streams for consumption by Alert Manager.
"""
import json
from typing import Optional
from redis import asyncio as aioredis

from shared.schemas import PriceTickMessage
from shared.utils import setup_logging


logger = setup_logging()


class RedisPublisher:
    """Publisher for Redis Streams."""
    
    STREAM_NAME = "price.tick"
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._message_count = 0
    
    async def publish_price_tick(self, message: PriceTickMessage):
        """
        Publish a price tick message to Redis Stream.
        
        Args:
            message: PriceTickMessage to publish
        """
        try:
            # Convert message to dict and then to JSON string
            message_data = message.model_dump()
            
            # Convert datetime to ISO format string
            message_data["timestamp"] = message_data["timestamp"].isoformat()
            
            # Publish to Redis Stream
            # XADD creates the stream if it doesn't exist
            await self.redis.xadd(
                self.STREAM_NAME,
                {"data": json.dumps(message_data)},
                maxlen=10000  # Keep only last 10k messages to prevent memory issues
            )
            
            self._message_count += 1
            
            # Log every 1000th message for monitoring
            if self._message_count % 1000 == 0:
                logger.info(
                    f"Published {self._message_count} messages to {self.STREAM_NAME}"
                )
        
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}", exc_info=True)
            raise
    
    def get_message_count(self) -> int:
        """Get total number of messages published."""
        return self._message_count
