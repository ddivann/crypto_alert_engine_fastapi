"""
Redis consumer for price tick events.
Consumes messages from Redis Streams and passes them to AlertChecker.
"""
import asyncio
import json
from datetime import datetime
from redis import asyncio as aioredis

from shared.schemas import PriceTickMessage
from shared.utils import setup_logging, parse_message_data


logger = setup_logging()


class RedisConsumer:
    """Consumer for Redis Streams."""
    
    STREAM_NAME = "price.tick"
    CONSUMER_GROUP = "alert-manager-group"
    CONSUMER_NAME = "alert-manager-1"
    
    def __init__(self, redis_client: aioredis.Redis, alert_checker):
        self.redis = redis_client
        self.alert_checker = alert_checker
        self.is_running = False
        self._message_count = 0
    
    async def start(self):
        """Start consuming messages from Redis Stream."""
        self.is_running = True
        
        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(
                self.STREAM_NAME,
                self.CONSUMER_GROUP,
                id="0",
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.CONSUMER_GROUP}")
        except Exception as e:
            # Group might already exist
            logger.info(f"Consumer group already exists or error: {e}")
        
        logger.info("Starting to consume messages")
        
        while self.is_running:
            try:
                # Read messages from stream
                messages = await self.redis.xreadgroup(
                    self.CONSUMER_GROUP,
                    self.CONSUMER_NAME,
                    {self.STREAM_NAME: ">"},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                if messages:
                    await self._process_messages(messages)
            
            except asyncio.CancelledError:
                logger.info("Consumer task cancelled")
                break
            except Exception as e:
                logger.error(f"Error consuming messages: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _process_messages(self, messages):
        """Process received messages."""
        for stream_name, message_list in messages:
            for message_id, message_data in message_list:
                try:
                    # Parse message using shared utility
                    data = json.loads(parse_message_data(message_data))
                    
                    # Convert to PriceTickMessage
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    price_tick = PriceTickMessage(**data)
                    
                    # Check alerts
                    await self.alert_checker.check_alerts(price_tick)
                    
                    # Acknowledge message
                    await self.redis.xack(self.STREAM_NAME, self.CONSUMER_GROUP, message_id)
                    
                    self._message_count += 1
                    
                    if self._message_count % 100 == 0:
                        logger.info(f"Processed {self._message_count} messages")
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    # Still acknowledge to avoid getting stuck
                    await self.redis.xack(self.STREAM_NAME, self.CONSUMER_GROUP, message_id)
    
    async def stop(self):
        """Stop consuming messages."""
        self.is_running = False
        logger.info("Consumer stopped")
    
    def get_message_count(self) -> int:
        """Get total number of messages processed."""
        return self._message_count
