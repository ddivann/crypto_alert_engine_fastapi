#!/bin/bash
# Quick Start Script for Crypto Alert Engine

set -e

echo "🚀 Crypto Alert Engine - Quick Start"
echo "===================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your TELEGRAM_BOT_TOKEN"
    echo "   You can get a token from @BotFather on Telegram"
    echo ""
    read -p "Do you want to edit .env now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
fi

echo ""
echo "🐳 Starting Docker containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service health..."

check_service() {
    local service=$1
    local port=$2
    local url="http://localhost:${port}/health"
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is not responding"
    fi
}

check_service "Price Fetcher" 8001
check_service "Alert Manager" 8002
check_service "Notification Service" 8003

echo ""
echo "📊 Service URLs:"
echo "   Price Fetcher:        http://localhost:8001"
echo "   Alert Manager:        http://localhost:8002"
echo "   Notification Service: http://localhost:8003"
echo ""
echo "📚 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🔍 To check status:"
echo "   curl http://localhost:8001/status"
echo "   curl http://localhost:8002/status"
echo "   curl http://localhost:8003/status"
echo ""
echo "➕ To create an alert:"
echo "   curl -X POST http://localhost:8002/alerts \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_id\": 1, \"symbol\": \"BTCUSDT\", \"condition\": \"above\", \"threshold\": 45000}'"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose down"
echo ""
echo "✨ All done! Your Crypto Alert Engine is running!"
echo "   Check EXAMPLES.md for more usage examples."
