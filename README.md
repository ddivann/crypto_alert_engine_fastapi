# Crypto Alert Engine

A microservices-based system for monitoring cryptocurrency prices and sending alerts when user-defined conditions are met.

## Architecture

The system consists of three main services:

1. **Price Fetcher Service** - Connects to crypto exchanges (Binance/Bybit) via WebSocket to fetch real-time price data
2. **Alert Manager Service** - Manages user alert rules and checks conditions against incoming price data
3. **Notification Service** - Sends notifications to users via Telegram/Email when alerts are triggered

## Technology Stack

- **FastAPI** - Web framework for all services
- **Redis Streams** - Message broker for inter-service communication
- **PostgreSQL** - Database for alert rules and user data
- **SQLAlchemy 2.0** - ORM for database interactions
- **aiogram** - Telegram bot framework
- **httpx/websockets** - Async HTTP and WebSocket clients

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Redis
- PostgreSQL

### Installation

```bash
# Clone the repository
git clone https://github.com/ddivann/crypto_alert_engine_fastapi.git
cd crypto_alert_engine_fastapi

# Install dependencies
pip install -r requirements.txt

# Run with Docker Compose
docker-compose up -d
```

## Project Structure

```
.
├── services/
│   ├── price_fetcher/      # Service A: Price data collector
│   ├── alert_manager/      # Service B: Alert business logic
│   └── notification_service/ # Service C: Notification sender
├── shared/
│   ├── schemas/            # Common data schemas
│   ├── config/             # Configuration management
│   └── utils/              # Shared utilities
├── tests/                  # Integration and unit tests
└── docker-compose.yml      # Docker orchestration
```

## Data Flow

```
Exchanges (Binance/Bybit)
    ↓ (WebSocket)
Price Fetcher Service
    ↓ (Redis: price.tick)
Alert Manager Service
    ↓ (Redis: alert.triggered)
Notification Service
    ↓
User (Telegram/Email)
```

## Development

Each service can be run independently or as part of the Docker Compose setup.

### Running Individual Services

```bash
# Price Fetcher
cd services/price_fetcher
uvicorn main:app --reload --port 8001

# Alert Manager
cd services/alert_manager
uvicorn main:app --reload --port 8002

# Notification Service
cd services/notification_service
uvicorn main:app --reload --port 8003
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=services tests/
```

## License

MIT
