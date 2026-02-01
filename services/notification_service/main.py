"""
Notification Service - Main Application
Sends notifications to users via Telegram when alerts are triggered.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from redis import asyncio as aioredis

from shared.config import get_settings
from shared.utils import setup_logging
from .consumer import NotificationConsumer
from .telegram_sender import TelegramSender


logger = setup_logging()
settings = get_settings()


# Global state
redis_client: aioredis.Redis = None
telegram_sender: TelegramSender = None
consumer: NotificationConsumer = None
background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global redis_client, telegram_sender, consumer
    
    logger.info("Starting Notification Service")
    
    # Initialize Redis
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    await redis_client.ping()
    logger.info("Connected to Redis")
    
    # Initialize Telegram sender
    if settings.telegram_bot_token:
        telegram_sender = TelegramSender(settings.telegram_bot_token)
        await telegram_sender.start()
        logger.info("Telegram bot initialized")
    else:
        logger.warning("Telegram bot token not provided, notifications will be logged only")
        telegram_sender = None
    
    # Initialize consumer
    consumer = NotificationConsumer(redis_client, telegram_sender)
    
    # Start consumer in background
    task = asyncio.create_task(consumer.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    logger.info("Notification Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Notification Service")
    await consumer.stop()
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    if telegram_sender:
        await telegram_sender.stop()
    
    await redis_client.close()
    logger.info("Notification Service stopped")


app = FastAPI(
    title="Notification Service",
    description="Sends notifications to users when alerts are triggered",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "notification-service",
        "redis_connected": redis_client is not None,
        "telegram_configured": telegram_sender is not None
    }


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "service": "notification-service",
        "notifications_sent": consumer.get_notification_count() if consumer else 0,
        "notifications_failed": consumer.get_failed_count() if consumer else 0,
        "telegram_configured": telegram_sender is not None,
        "redis_connected": redis_client is not None
    }
