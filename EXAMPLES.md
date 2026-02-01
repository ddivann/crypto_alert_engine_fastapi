# Example Usage Guide

This guide demonstrates how to use the Crypto Alert Engine system.

## Setup

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:
- Add your Telegram bot token if using Telegram notifications
- Adjust database credentials if needed
- Configure exchange settings

### 2. Start the System

Using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Redis (message broker) on port 6379
- PostgreSQL (database) on port 5432
- Price Fetcher service on port 8001
- Alert Manager service on port 8002
- Notification service on port 8003

### 3. Verify Services

Check health of all services:

```bash
# Price Fetcher
curl http://localhost:8001/health

# Alert Manager
curl http://localhost:8002/health

# Notification Service
curl http://localhost:8003/health
```

## Creating Alerts

### Example 1: Create an Alert for BTC Above $45,000

```bash
curl -X POST http://localhost:8002/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "condition": "above",
    "threshold": 45000.0
  }'
```

Response:
```json
{
  "id": 1,
  "user_id": 1,
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "condition": "above",
  "threshold": 45000.0,
  "is_active": true,
  "created_at": "2024-01-01T12:00:00"
}
```

### Example 2: Create an Alert for ETH Below $3,000

```bash
curl -X POST http://localhost:8002/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "symbol": "ETHUSDT",
    "exchange": "binance",
    "condition": "below",
    "threshold": 3000.0
  }'
```

## Managing Alerts

### Get All Alerts for a User

```bash
curl http://localhost:8002/alerts/1
```

Response:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "condition": "above",
    "threshold": 45000.0,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00"
  },
  {
    "id": 2,
    "user_id": 1,
    "symbol": "ETHUSDT",
    "exchange": "binance",
    "condition": "below",
    "threshold": 3000.0,
    "is_active": true,
    "created_at": "2024-01-01T12:05:00"
  }
]
```

### Delete an Alert

```bash
curl -X DELETE http://localhost:8002/alerts/1
```

## Managing Subscriptions

The Price Fetcher service subscribes to BTCUSDT and ETHUSDT by default. You can add more:

### Subscribe to a New Symbol

```bash
curl -X POST http://localhost:8001/subscribe/SOLUSDT
```

### Unsubscribe from a Symbol

```bash
curl -X POST http://localhost:8001/unsubscribe/SOLUSDT
```

## Monitoring

### Check Service Status

Get detailed status of each service:

```bash
# Price Fetcher - see subscriptions and messages published
curl http://localhost:8001/status

# Alert Manager - see alerts checked and triggered
curl http://localhost:8002/status

# Notification Service - see notifications sent
curl http://localhost:8003/status
```

Example response from Price Fetcher:
```json
{
  "service": "price-fetcher",
  "subscriptions": ["btcusdt", "ethusdt"],
  "messages_published": 1523,
  "redis_connected": true
}
```

## Data Flow Example

Here's what happens when an alert is triggered:

1. **Price Update**: Binance sends price update for BTCUSDT at $45,100
2. **Price Fetcher**: Receives WebSocket message, publishes to Redis stream `price.tick`
3. **Alert Manager**: 
   - Consumes message from `price.tick` stream
   - Checks active alerts for BTCUSDT
   - Finds alert with condition "above $45,000"
   - Publishes to Redis stream `alert.triggered`
4. **Notification Service**:
   - Consumes message from `alert.triggered` stream
   - Formats notification message
   - Sends Telegram message to user

## Telegram Bot Setup

To receive notifications via Telegram:

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get the bot token
3. Add token to `.env` file as `TELEGRAM_BOT_TOKEN`
4. Restart the notification service
5. Start a chat with your bot
6. Create alerts (the user_id in alerts should correspond to your Telegram chat_id)

## Stopping the System

```bash
docker-compose down
```

To also remove volumes (database data):

```bash
docker-compose down -v
```

## Troubleshooting

### Service won't start

Check logs:
```bash
docker-compose logs price-fetcher
docker-compose logs alert-manager
docker-compose logs notification-service
```

### No notifications received

1. Check notification service logs
2. Verify Telegram bot token is set
3. Ensure user_id mapping is correct
4. Check Redis connectivity

### Price updates not working

1. Check Price Fetcher logs
2. Verify WebSocket connection to exchange
3. Check Redis is running and accessible
4. Verify exchange API is not rate limiting

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=services tests/
```

### Running Services Locally (without Docker)

1. Start Redis:
```bash
redis-server
```

2. Start PostgreSQL:
```bash
# Use your local PostgreSQL installation
```

3. Set environment variables:
```bash
export REDIS_HOST=localhost
export POSTGRES_HOST=localhost
export TELEGRAM_BOT_TOKEN=your_token_here
```

4. Run each service:
```bash
# Price Fetcher
cd /path/to/repo
PYTHONPATH=. uvicorn services.price_fetcher.main:app --reload --port 8001

# Alert Manager
PYTHONPATH=. uvicorn services.alert_manager.main:app --reload --port 8002

# Notification Service
PYTHONPATH=. uvicorn services.notification_service.main:app --reload --port 8003
```
