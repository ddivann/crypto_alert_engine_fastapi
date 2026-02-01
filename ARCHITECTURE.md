# Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Crypto Alert Engine System                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  Binance Exchange   │
│   (WebSocket API)   │
└──────────┬──────────┘
           │ Real-time price stream
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SERVICE A: Price Fetcher (Port 8001)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  • WebSocket Client with auto-reconnect                                      │
│  • Rate limiting & backpressure handling                                     │
│  • Default subscriptions: BTCUSDT, ETHUSDT                                   │
│  • FastAPI REST endpoints for subscription management                        │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ Publishes PriceTickMessage
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REDIS STREAMS (Message Broker)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stream: "price.tick"                                                        │
│  • Consumer groups for reliable delivery                                     │
│  • Message acknowledgment                                                    │
│  • Max length limit (10k messages)                                           │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ Consumes messages
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SERVICE B: Alert Manager (Port 8002)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  • FastAPI REST API for alert CRUD                                           │
│  • PostgreSQL database (alert_rules, alert_history)                          │
│  • Alert evaluation engine (above/below conditions)                          │
│  • Throttling (60-minute cooldown)                                           │
│  • Deduplication logic                                                       │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ Publishes AlertTriggeredMessage
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REDIS STREAMS (Message Broker)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Stream: "alert.triggered"                                                   │
│  • Consumer groups                                                           │
│  • Dead Letter Queue (DLQ) for failures                                      │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ Consumes messages
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SERVICE C: Notification Service (Port 8003)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Telegram bot integration (aiogram)                                        │
│  • Retry logic with exponential backoff                                      │
│  • HTML message formatting                                                   │
│  • Dead Letter Queue for failed notifications                                │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │ Sends notification
           ▼
┌─────────────────────┐
│   Telegram User     │
│  (Alert Received)   │
└─────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                            Supporting Services                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐      ┌──────────────────┐                            │
│  │   PostgreSQL     │      │      Redis       │                             │
│  │   (Port 5432)    │      │   (Port 6379)    │                             │
│  │                  │      │                  │                              │
│  │  • alert_rules   │      │  • price.tick    │                             │
│  │  • alert_history │      │  • alert.triggered│                            │
│  └──────────────────┘      └──────────────────┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Endpoints                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Price Fetcher (8001):              Alert Manager (8002):                    │
│  • GET  /health                     • GET  /health                           │
│  • GET  /status                     • GET  /status                           │
│  • POST /subscribe/{symbol}         • POST /alerts                           │
│  • POST /unsubscribe/{symbol}       • GET  /alerts/{user_id}                 │
│                                     • DELETE /alerts/{alert_id}              │
│                                                                              │
│  Notification Service (8003):                                                │
│  • GET  /health                                                              │
│  • GET  /status                                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                            Message Schemas                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PriceTickMessage:                  AlertTriggeredMessage:                   │
│  {                                  {                                        │
│    "version": "1.0",                  "version": "1.0",                      │
│    "message_type": "price.tick",      "message_type": "alert.triggered",    │
│    "timestamp": "...",                "timestamp": "...",                    │
│    "symbol": "BTCUSDT",               "alert_id": 123,                       │
│    "exchange": "binance",             "user_id": 456,                        │
│    "price": 45000.50,                 "symbol": "BTCUSDT",                   │
│    "volume": 123.45                   "condition": "above",                  │
│  }                                    "threshold": 45000.0,                  │
│                                       "current_price": 45001.0,              │
│                                       "message": "..."                        │
│                                    }                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### 🎯 Reliability
- Auto-reconnect for WebSocket connections
- Message acknowledgment in Redis Streams
- Retry logic with exponential backoff
- Dead Letter Queue for failed messages

### ⚡ Performance
- Asynchronous operations throughout
- Redis Streams for high-throughput messaging
- Efficient database queries with SQLAlchemy
- Connection pooling

### 🔒 Security
- Environment-based configuration
- Input validation with Pydantic
- SQL injection prevention via ORM
- No hardcoded secrets

### 📊 Observability
- Structured JSON logging
- Health check endpoints
- Status endpoints with metrics
- Error tracking

### 🔧 Scalability
- Stateless services
- Horizontal scaling support
- Consumer groups for load balancing
- Database connection pooling

## Deployment

All services are containerized and orchestrated with Docker Compose:

```bash
docker-compose up -d
```

Services automatically:
- Connect to Redis and PostgreSQL
- Create database tables
- Start consuming messages
- Handle reconnections on failure
