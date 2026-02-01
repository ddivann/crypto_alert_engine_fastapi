"""
Price Fetcher Service - Main Application
Connects to crypto exchanges via WebSocket and publishes price updates to Redis Streams.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from redis import asyncio as aioredis

from shared.config import get_settings
from shared.utils import setup_logging
from .websocket_client import BinanceWebSocketClient
from .publisher import RedisPublisher


logger = setup_logging()
settings = get_settings()


# Global state
redis_client: aioredis.Redis = None
ws_client: BinanceWebSocketClient = None
publisher: RedisPublisher = None
background_tasks = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    global redis_client, ws_client, publisher
    
    logger.info("Starting Price Fetcher Service")
    
    # Initialize Redis
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    await redis_client.ping()
    logger.info("Connected to Redis")
    
    # Initialize publisher
    publisher = RedisPublisher(redis_client)
    
    # Initialize WebSocket client
    ws_client = BinanceWebSocketClient(publisher)
    
    # Start WebSocket connection in background
    task = asyncio.create_task(ws_client.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    logger.info("Price Fetcher Service started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Price Fetcher Service")
    await ws_client.stop()
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    await redis_client.close()
    logger.info("Price Fetcher Service stopped")


app = FastAPI(
    title="Price Fetcher Service",
    description="Fetches cryptocurrency prices from exchanges and publishes to message broker",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "price-fetcher",
        "redis_connected": redis_client is not None,
        "websocket_connected": ws_client.is_connected() if ws_client else False
    }


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "service": "price-fetcher",
        "subscriptions": ws_client.get_subscriptions() if ws_client else [],
        "messages_published": publisher.get_message_count() if publisher else 0,
        "redis_connected": redis_client is not None
    }


@app.post("/subscribe/{symbol}")
async def subscribe_symbol(symbol: str):
    """Subscribe to a trading pair."""
    if ws_client:
        await ws_client.subscribe(symbol)
        return {"status": "subscribed", "symbol": symbol}
    return {"status": "error", "message": "WebSocket client not initialized"}


@app.post("/unsubscribe/{symbol}")
async def unsubscribe_symbol(symbol: str):
    """Unsubscribe from a trading pair."""
    if ws_client:
        await ws_client.unsubscribe(symbol)
        return {"status": "unsubscribed", "symbol": symbol}
    return {"status": "error", "message": "WebSocket client not initialized"}
