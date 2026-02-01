"""
Redis consumer for alert.triggered events.
Consumes alert messages and sends notifications.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional
from redis import asyncio as aioredis

from shared.schemas import AlertTriggeredMessage
from shared.utils import setup_logging


logger = setup_logging()


class NotificationConsumer:
    """Consumer for alert.triggered events."""
    
    STREAM_NAME = "alert.triggered"
    CONSUMER_GROUP = "notification-service-group"
    CONSUMER_NAME = "notification-service-1"
    DLQ_STREAM = "alert.triggered.dlq"  # Dead Letter Queue
    
    def __init__(self, redis_client: aioredis.Redis, telegram_sender):
        self.redis = redis_client
        self.telegram_sender = telegram_sender
        self.is_running = False
        self._notification_count = 0
        self._failed_count = 0
    
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
            logger.info(f"Consumer group already exists or error: {e}")
        
        logger.info("Starting to consume alert notifications")
        
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
        """Process received alert messages."""
        for stream_name, message_list in messages:
            for message_id, message_data in message_list:
                try:
                    # Parse message
                    data = json.loads(
                        message_data[b"data"] if isinstance(message_data[b"data"], bytes) 
                        else message_data["data"]
                    )
                    
                    # Convert to AlertTriggeredMessage
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    alert = AlertTriggeredMessage(**data)
                    
                    # Send notification
                    success = await self._send_notification(alert)
                    
                    if success:
                        # Acknowledge message
                        await self.redis.xack(self.STREAM_NAME, self.CONSUMER_GROUP, message_id)
                        self._notification_count += 1
                        
                        if self._notification_count % 10 == 0:
                            logger.info(f"Sent {self._notification_count} notifications")
                    else:
                        # Move to dead letter queue
                        await self._move_to_dlq(message_id, message_data)
                        await self.redis.xack(self.STREAM_NAME, self.CONSUMER_GROUP, message_id)
                        self._failed_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing notification: {e}", exc_info=True)
                    # Still acknowledge to avoid getting stuck
                    await self.redis.xack(self.STREAM_NAME, self.CONSUMER_GROUP, message_id)
                    self._failed_count += 1
    
    async def _send_notification(self, alert: AlertTriggeredMessage) -> bool:
        """
        Send notification for an alert.
        
        Args:
            alert: Alert message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if self.telegram_sender:
            # Format message
            formatted_message = self.telegram_sender.format_alert_message({
                "symbol": alert.symbol,
                "current_price": alert.current_price,
                "condition": alert.condition.value,
                "threshold": alert.threshold,
                "message": alert.message
            })
            
            # Send via Telegram
            return await self.telegram_sender.send_notification(
                alert.user_id,
                formatted_message
            )
        else:
            # Log notification if Telegram not configured
            logger.info(f"[NOTIFICATION] User {alert.user_id}: {alert.message}")
            return True
    
    async def _move_to_dlq(self, message_id: str, message_data: dict):
        """Move failed message to dead letter queue."""
        try:
            await self.redis.xadd(
                self.DLQ_STREAM,
                {
                    "original_id": message_id,
                    "data": message_data.get("data", ""),
                    "failed_at": datetime.utcnow().isoformat()
                },
                maxlen=1000
            )
            logger.info(f"Moved message {message_id} to DLQ")
        except Exception as e:
            logger.error(f"Error moving to DLQ: {e}", exc_info=True)
    
    async def stop(self):
        """Stop consuming messages."""
        self.is_running = False
        logger.info("Notification consumer stopped")
    
    def get_notification_count(self) -> int:
        """Get total number of notifications sent."""
        return self._notification_count
    
    def get_failed_count(self) -> int:
        """Get total number of failed notifications."""
        return self._failed_count
