#!/bin/bash

# AutoTest-RL Quick Start Script
# This script helps you get started quickly with the AutoTest-RL system

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║           AutoTest-RL Quick Start Script                     ║"
echo "║   Intelligent API Testing with Reinforcement Learning        ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"
echo -e "${GREEN}✓ Docker Compose is installed${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.template .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Please edit .env file and add your API keys!${NC}"
    echo ""
    echo "   Required API keys:"
    echo "   1. GROQ_API_KEY (Get from: https://console.groq.com/)"
    echo "   2. MISTRAL_API_KEY (Get from: https://console.mistral.ai/)"
    echo ""
    echo "   Optional:"
    echo "   - OPENAI_API_KEY (https://platform.openai.com/api-keys)"
    echo "   - ANTHROPIC_API_KEY (https://console.anthropic.com/)"
    echo ""
    read -p "Press Enter after you've added your API keys to .env..."
fi

# Check if API keys are set
if ! grep -q "GROQ_API_KEY=gsk_" .env 2>/dev/null && ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null && ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: No API keys detected in .env file${NC}"
    echo "   The system may not work without at least one LLM API key."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Please add API keys to .env and run this script again."
        exit 1
    fi
fi

# Check if containers are already running
if docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Some containers are already running${NC}"
    read -p "Do you want to restart them? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}🔄 Restarting services...${NC}"
        docker-compose down
    else
        echo -e "${GREEN}✓ Using existing containers${NC}"
        echo ""
        echo -e "${GREEN}Services are running at:${NC}"
        echo "  - API:      http://localhost:8000"
        echo "  - Docs:     http://localhost:8000/docs"
        echo "  - ChromaDB: http://localhost:8001"
        echo "  - Flower:   http://localhost:5555"
        echo ""
        echo "Run 'make logs' to view logs"
        echo "Run 'make health' to check service health"
        exit 0
    fi
fi

# Start services
echo -e "${BLUE}🚀 Building and starting services...${NC}"
echo "   This may take a few minutes on first run..."
echo ""

docker-compose up -d --build

echo ""
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"

# Wait for API to be ready
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is ready!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo ""
        echo -e "${RED}❌ API did not start within expected time${NC}"
        echo "   Check logs with: docker-compose logs api"
        exit 1
    fi
done

echo ""

# Check ChromaDB
if curl -f http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ChromaDB is ready!${NC}"
else
    echo -e "${YELLOW}⚠️  ChromaDB may not be ready yet${NC}"
fi

# Check Redis
if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is ready!${NC}"
else
    echo -e "${YELLOW}⚠️  Redis may not be ready yet${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║                   🎉 Setup Complete! 🎉                       ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📍 Services are running at:${NC}"
echo ""
echo "  🌐 API:          http://localhost:8000"
echo "  📚 Swagger Docs: http://localhost:8000/docs"
echo "  📖 ReDoc:        http://localhost:8000/redoc"
echo "  🗄️  ChromaDB:    http://localhost:8001"
echo "  🌸 Flower:       http://localhost:5555"
echo ""

echo -e "${BLUE}🎯 Quick Commands:${NC}"
echo ""
echo "  make logs        - View all logs"
echo "  make logs-api    - View API logs"
echo "  make health      - Check service health"
echo "  make ps          - List running services"
echo "  make shell       - Open bash shell"
echo "  make docs        - Open API docs in browser"
echo "  make down        - Stop all services"
echo ""

echo -e "${BLUE}📖 Documentation:${NC}"
echo ""
echo "  README.md          - Full documentation"
echo "  QUICKSTART.md      - Quick start guide"
echo "  DOCKER_COMMANDS.md - Docker commands reference"
echo "  PROJECT_STATUS.md  - Current project status"
echo ""

echo -e "${BLUE}🧪 Try it out:${NC}"
echo ""
echo "  # Check health"
echo "  curl http://localhost:8000/health"
echo ""
echo "  # View API info"
echo "  curl http://localhost:8000/api/v1/info"
echo ""
echo "  # Or open Swagger UI in your browser:"
echo "  http://localhost:8000/docs"
echo ""

echo -e "${GREEN}✨ Happy Testing! ✨${NC}"
echo ""

# Optionally open browser
if command -v xdg-open &> /dev/null; then
    read -p "Open API docs in browser? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        xdg-open http://localhost:8000/docs 2>/dev/null &
    fi
elif command -v open &> /dev/null; then
    read -p "Open API docs in browser? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        open http://localhost:8000/docs 2>/dev/null &
    fi
fi
