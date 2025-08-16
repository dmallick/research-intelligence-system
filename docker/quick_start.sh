#!/bin/bash

echo "🚀 Starting Multi-Agent Research System - Full Setup"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"

# Start the database and services
echo "🐳 Starting database and supporting services..."
docker-compose -f docker/docker-compose.dev.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if PostgreSQL is ready
echo "🔍 Checking PostgreSQL connection..."
until docker-compose -f docker/docker-compose.dev.yml exec postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "⏳ PostgreSQL is starting up..."
    sleep 3
done

echo "✅ PostgreSQL is ready!"

# Check if Redis is ready
echo "🔍 Checking Redis connection..."
until docker-compose -f docker/docker-compose.dev.yml exec redis redis-cli ping > /dev/null 2>&1; do
    echo "⏳ Redis is starting up..."
    sleep 2
done

echo "✅ Redis is ready!"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys before running the application"
fi

# Create logs directory
mkdir -p logs

# Update .env with correct database URL for Docker
echo "🔧 Updating database configuration for Docker..."
if grep -q "localhost:5432" .env; then
    # Update database URL to use Docker container
    sed -i.bak 's/localhost:5432/localhost:5432/g' .env
    echo "✅ Database URL configured for Docker"
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - OPENAI_API_KEY=your_actual_key"
echo "   - SECRET_KEY=your_secret_key"
echo ""
echo "2. Start the FastAPI application:"
echo "   python -m uvicorn api.main:app --reload"
echo ""
echo "3. Check the services are running:"
echo "   - API: http://localhost:8000"
echo "   - Health: http://localhost:8000/health"
echo ""
echo "4. To stop services later:"
echo "   docker-compose -f docker/docker-compose.dev.yml down"