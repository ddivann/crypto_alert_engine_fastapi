"""
WebSocket client for connecting to crypto exchanges.
Handles connection management, reconnection, and rate limiting.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional
import websockets
from websockets.exceptions import WebSocketException

from shared.config import get_settings
from shared.utils import setup_logging, RetryConfig
from shared.schemas import PriceTickMessage


logger = setup_logging()
settings = get_settings()


class BinanceWebSocketClient:
    """WebSocket client for Binance exchange."""
    
    def __init__(self, publisher):
        self.publisher = publisher
        self.ws_url = settings.binance_ws_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscriptions: Set[str] = {"btcusdt", "ethusdt"}  # Default subscriptions
        self.is_running = False
        self.retry_config = RetryConfig(
            max_attempts=settings.max_reconnect_attempts,
            initial_delay=settings.reconnect_delay
        )
        self._message_count = 0
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.websocket is not None and self.websocket.open
    
    def get_subscriptions(self) -> list:
        """Get list of active subscriptions."""
        return list(self.subscriptions)
    
    async def start(self):
        """Start WebSocket connection with auto-reconnect."""
        self.is_running = True
        attempt = 0
        
        while self.is_running:
            try:
                await self._connect()
                attempt = 0  # Reset attempt counter on successful connection
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                
                if attempt >= self.retry_config.max_attempts:
                    logger.error("Max reconnection attempts reached")
                    break
                
                delay = self.retry_config.get_delay(attempt)
                logger.info(f"Reconnecting in {delay} seconds (attempt {attempt + 1})")
                await asyncio.sleep(delay)
                attempt += 1
    
    async def _connect(self):
        """Establish WebSocket connection and handle messages."""
        # Build stream URL with subscriptions
        streams = [f"{symbol.lower()}@trade" for symbol in self.subscriptions]
        stream_url = f"{self.ws_url}/stream?streams={'/'.join(streams)}"
        
        logger.info(f"Connecting to Binance WebSocket: {stream_url}")
        
        async with websockets.connect(stream_url) as websocket:
            self.websocket = websocket
            logger.info("Connected to Binance WebSocket")
            
            async for message in websocket:
                if not self.is_running:
                    break
                
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _handle_message(self, message: str):
        """Process incoming WebSocket message."""
        data = json.loads(message)
        
        # Binance multi-stream format
        if "stream" in data and "data" in data:
            stream_name = data["stream"]
            trade_data = data["data"]
            
            # Extract symbol from stream name (e.g., "btcusdt@trade" -> "BTCUSDT")
            symbol = stream_name.split("@")[0].upper()
            
            # Create price tick message
            price_tick = PriceTickMessage(
                symbol=symbol,
                exchange="binance",
                price=float(trade_data["p"]),  # Price
                volume=float(trade_data["q"]),  # Quantity
                timestamp=datetime.utcfromtimestamp(trade_data["T"] / 1000)  # Trade time
            )
            
            # Publish to Redis
            await self.publisher.publish_price_tick(price_tick)
            self._message_count += 1
            
            if self._message_count % 100 == 0:
                logger.info(f"Published {self._message_count} price updates")
    
    async def subscribe(self, symbol: str):
        """Add a new trading pair subscription."""
        self.subscriptions.add(symbol.lower())
        logger.info(f"Added subscription for {symbol}")
        # Note: In production, you'd need to send a subscribe message to the WebSocket
        # For simplicity, we'll require a reconnection to add new subscriptions
    
    async def unsubscribe(self, symbol: str):
        """Remove a trading pair subscription."""
        self.subscriptions.discard(symbol.lower())
        logger.info(f"Removed subscription for {symbol}")
    
    async def stop(self):
        """Stop WebSocket connection."""
        self.is_running = False
        if self.websocket and self.websocket.open:
            await self.websocket.close()
            logger.info("WebSocket connection closed")
