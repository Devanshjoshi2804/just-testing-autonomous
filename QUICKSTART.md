# ⚡ Quick Start Guide - AutoTest-RL

Get up and running in 5 minutes!

## 🎯 Prerequisites

- Docker & Docker Compose installed
- At least ONE LLM API key (Groq recommended for free tier)
- 8GB+ RAM available for Docker

## 🚀 Super Quick Start (3 Steps)

### Step 1: Setup Environment

```bash
# Copy environment template
cp .env.template .env

# Edit with your API keys (minimum: GROQ_API_KEY + MISTRAL_API_KEY)
nano .env
```

### Step 2: Start Services

```bash
# Using Make (recommended)
make up-build

# Or using Docker Compose directly
docker-compose up -d --build
```

### Step 3: Verify

```bash
# Check health
make health

# Or manually
curl http://localhost:8000/health
```

**Done!** 🎉 Your API is running at http://localhost:8000

---

## 📋 Detailed Setup

### 1. Get API Keys (Free Tiers Available)

#### Groq (Recommended - Fast & Free)
1. Go to https://console.groq.com/
2. Sign up for free account
3. Create API key
4. Copy to `.env` as `GROQ_API_KEY`

#### Mistral (Required for Embeddings)
1. Go to https://console.mistral.ai/
2. Sign up for free account
3. Create API key
4. Copy to `.env` as `MISTRAL_API_KEY`

#### Optional: OpenAI or Anthropic
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/

### 2. Configure Environment

```bash
# Minimum configuration in .env
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
MISTRAL_API_KEY=xxxxxxxxxxxxx

# Choose your LLM provider
LLM_PROVIDER=groq  # or openai, anthropic
LLM_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
```

### 3. Start the System

```bash
# Method 1: Using Make (easiest)
make setup        # Creates .env if not exists
make up-build     # Builds and starts all services
make logs-api     # View logs

# Method 2: Using Docker Compose
docker-compose up -d --build
docker-compose logs -f api
```

### 4. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Main backend API |
| **Docs** | http://localhost:8000/docs | Swagger UI (interactive) |
| **ReDoc** | http://localhost:8000/redoc | Alternative docs |
| **Flower** | http://localhost:5555 | Celery task monitor |
| **ChromaDB** | http://localhost:8001 | Vector database |

---

## 🧪 Test Your Setup

### 1. Health Check

```bash
# Using Make
make health

# Using curl
curl http://localhost:8000/health

# Expected output:
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0"
}
```

### 2. API Info

```bash
curl http://localhost:8000/api/v1/info

# Shows your configuration
{
  "environment": "development",
  "llm_provider": "groq",
  "llm_model": "meta-llama/llama-4-maverick-17b-128e-instruct",
  ...
}
```

### 3. Check Services

```bash
# List running services
make ps

# Or
docker-compose ps

# Expected: 6 services running
# - api
# - chromadb
# - redis
# - celery_worker
# - celery_beat
# - flower
```

---

## 🎮 Using the System

### Method 1: Swagger UI (Easiest)

1. Open http://localhost:8000/docs
2. Try the `/health` endpoint
3. Upload your API documentation (coming soon)
4. Start testing (coming soon)

### Method 2: cURL

```bash
# Health check
curl http://localhost:8000/health

# API info (debug mode only)
curl http://localhost:8000/api/v1/info

# Upload document (endpoint coming soon)
# curl -X POST http://localhost:8000/api/v1/documents/upload \
#   -F "file=@api-doc.pdf"
```

### Method 3: Python Client

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Upload document (coming soon)
# with open("api-doc.pdf", "rb") as f:
#     response = requests.post(
#         "http://localhost:8000/api/v1/documents/upload",
#         files={"file": f}
#     )
```

---

## 🛠️ Common Commands

### Service Management

```bash
make up          # Start services
make down        # Stop services
make restart     # Restart services
make logs        # View all logs
make logs-api    # View API logs
make ps          # List services
```

### Development

```bash
make shell       # Open bash shell in API container
make python      # Open Python shell
make test        # Run tests
make test-cov    # Run tests with coverage
```

### Monitoring

```bash
make health      # Check all services
make stats       # Show resource usage
make docs        # Open API docs in browser
make flower      # Open Flower dashboard
```

### Cleanup

```bash
make clean       # Remove containers & volumes (⚠️ deletes data)
make rebuild     # Full rebuild from scratch
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
make logs

# Check if ports are available
lsof -i :8000
lsof -i :8001
lsof -i :6379
lsof -i :5555

# Kill conflicting processes
kill -9 <PID>

# Try rebuilding
make down
make rebuild
```

### ChromaDB Connection Issues

```bash
# Restart ChromaDB
docker-compose restart chromadb

# Check logs
docker-compose logs chromadb

# Verify it's running
curl http://localhost:8001/api/v1/heartbeat
```

### Redis Connection Issues

```bash
# Restart Redis
docker-compose restart redis

# Check if Redis is responding
redis-cli -h localhost -p 6379 ping
# Expected: PONG
```

### API Not Responding

```bash
# Check API logs
make logs-api

# Restart API
docker-compose restart api

# Check if it's running
docker-compose ps api

# Enter container to debug
make shell
```

### Out of Memory

```bash
# Increase Docker memory (Docker Desktop)
# Settings → Resources → Memory → 8GB+

# Or reduce parallelization in .env
MAX_PARALLEL_TESTS=2
```

### Permission Errors

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/ logs/ results/

# Restart services
make restart
```

---

## 🎓 Next Steps

### 1. Learn the System
- Read [README.md](README.md) for full documentation
- Check [DOCKER_COMMANDS.md](DOCKER_COMMANDS.md) for all Docker commands
- Explore API docs at http://localhost:8000/docs

### 2. Configure Advanced Settings
- Edit `.env` for custom configuration
- Adjust LLM models, RL parameters, retry logic
- See `.env.template` for all options

### 3. Start Testing
- Upload your first API documentation
- Watch the system analyze and test automatically
- View results in Flower dashboard

### 4. Train RL Agent (Optional)
```bash
# Start RL training
make train-rl

# Monitor training logs
docker-compose logs -f rl_trainer
```

---

## 💡 Pro Tips

1. **Use Groq** for fast, free LLM inference
2. **Enable curiosity mode** in .env for better exploration
3. **Scale workers** based on your CPU: `make scale-workers N=4`
4. **Backup ChromaDB** regularly: `make backup-db`
5. **Check Flower** at http://localhost:5555 to monitor task processing
6. **Use `make health`** before reporting issues
7. **View logs** with `make logs-api` to debug problems
8. **Restart services** with `make restart` after .env changes

---

## 🆘 Get Help

### Quick Diagnostics

```bash
# Full health check
make health

# Check all logs
make logs

# Check resource usage
make stats

# Check running services
make ps
```

### Common Issues & Fixes

| Issue | Command | Fix |
|-------|---------|-----|
| Port already in use | `lsof -i :8000` | Kill process or change port |
| Service won't start | `make logs` | Check error messages |
| Out of memory | `docker stats` | Increase Docker memory limit |
| Stale containers | `make clean` | Remove and rebuild |
| API not responding | `make restart` | Restart services |

---

## ✅ Checklist

Before asking for help, verify:

- [ ] Docker & Docker Compose installed
- [ ] `.env` file created with API keys
- [ ] All services running: `make ps`
- [ ] Health check passes: `make health`
- [ ] No port conflicts: ports 8000, 8001, 6379, 5555 available
- [ ] Sufficient memory: 8GB+ allocated to Docker
- [ ] Logs checked: `make logs` shows no critical errors

---

**Ready to start testing!** 🚀

Upload your API documentation and watch the magic happen!
