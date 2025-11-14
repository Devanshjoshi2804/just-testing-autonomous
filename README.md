# 🚀 AutoTest-RL: Intelligent API Testing with Reinforcement Learning

**Backend-only system** that analyzes API documentation (PDF/JSON) and performs comprehensive automated testing using LLMs, RAG, and Reinforcement Learning.

## 🌟 Features

- **📄 Smart Document Understanding**: Upload PDF/JSON API docs → System extracts endpoints automatically
- **🧠 LLM-Powered Test Generation**: AI agents generate complete test cases using RAG
- **🔄 Intelligent Retry Logic**: Auto-fixes failed tests by analyzing error responses
- **🎯 Reinforcement Learning**: Learns optimal API testing sequences over time
- **💾 Dual ChromaDB Architecture**: Separate stores for documentation and test flow state
- **⚡ Async Execution**: Parallel test execution with smart dependency management
- **📊 Comprehensive Reporting**: Detailed test results with coverage analysis

## 🏗️ Architecture

```
API Documentation → Document Parser → RAG System → Multi-Agent LLM → RL Optimizer → Test Executor → Results
```

**Key Components:**
- **Document Understanding**: LlamaParse, PyMuPDF4LLM
- **RAG System**: ChromaDB (Doc DB + Flow DB) + Mistral Embeddings
- **LLM Agents**: GPT-4o / Claude 3.5 / Llama 4 (configurable)
- **RL Engine**: PPO with curiosity-driven exploration
- **Execution**: HTTPX async client with smart retry

## 🐳 Docker Quick Start

### Prerequisites
- Docker & Docker Compose installed
- API keys for LLM providers (see Setup section)

### 1. Clone & Setup Environment

```bash
# Clone repository
cd just-testing-autonomous

# Copy environment template
cp .env.template .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

### 2. Start All Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service health
docker-compose ps
```

### 3. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ChromaDB**: http://localhost:8001
- **Redis**: localhost:6379
- **Flower** (Celery Monitor): http://localhost:5555

### 4. Upload API Documentation

```bash
# Example: Upload PDF documentation
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@your-api-doc.pdf"

# Start automated testing
curl -X POST http://localhost:8000/api/v1/tests/start \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc_id_from_upload"}'
```

## 📦 Services Overview

### Core Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | Main FastAPI backend |
| `chromadb` | 8001 | Vector database for RAG |
| `redis` | 6379 | Task queue & caching |
| `celery_worker` | - | Background task processing |
| `celery_beat` | - | Periodic task scheduler |
| `flower` | 5555 | Celery monitoring dashboard |

### Optional Services

| Service | Port | Description | How to Start |
|---------|------|-------------|--------------|
| `rl_trainer` | - | RL model training | `docker-compose --profile training up rl_trainer` |

## 🔧 Configuration

### Minimal Required API Keys

You need **at least ONE** LLM provider:

```env
# Option 1: Groq (RECOMMENDED - Fast & Free Tier)
GROQ_API_KEY=your_groq_api_key

# Option 2: OpenAI
OPENAI_API_KEY=your_openai_api_key

# Option 3: Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key

# Required for embeddings
MISTRAL_API_KEY=your_mistral_api_key
```

### Full Configuration

See `.env.template` for all available options:
- LLM model selection
- RAG parameters (chunk size, top-k retrieval)
- RL hyperparameters
- Retry logic settings
- Logging configuration

## 🛠️ Development Mode

### Hot Reload Enabled

The Docker setup includes volume mounts for live code reloading:

```bash
# Make changes to src/ - API automatically reloads
vim src/api/main.py

# Changes are reflected immediately
docker-compose logs -f api
```

### Run Tests

```bash
# Run tests inside container
docker-compose exec api pytest tests/ -v

# With coverage
docker-compose exec api pytest tests/ --cov=src --cov-report=html
```

### Access Python Shell

```bash
# Open Python shell with app context
docker-compose exec api python

# Or use IPython
docker-compose exec api pip install ipython
docker-compose exec api ipython
```

## 📊 Monitoring & Debugging

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f celery_worker

# Tail last 100 lines
docker-compose logs --tail=100 api
```

### Monitor Celery Tasks

Open Flower dashboard: http://localhost:5555

- View active tasks
- Monitor task success/failure rates
- Inspect worker performance

### ChromaDB Collections

```bash
# List collections via API
curl http://localhost:8001/api/v1/collections
```

## 🚀 Production Deployment

### 1. Update Environment

```env
ENVIRONMENT=production
DEBUG=false
API_RELOAD=false
LOG_LEVEL=WARNING
```

### 2. Build Production Image

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
```

### 3. Run with Resource Limits

```bash
docker-compose up -d --scale celery_worker=4
```

### 4. Enable HTTPS (Recommended)

Add Nginx reverse proxy:

```yaml
# docker-compose.prod.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

## 🧪 Usage Examples

### Example 1: Test Cargodham API

```python
import requests

# Upload API documentation
with open("cargodham-api.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/documents/upload",
        files={"file": f}
    )
doc_id = response.json()["document_id"]

# Start automated testing
response = requests.post(
    "http://localhost:8000/api/v1/tests/start",
    json={
        "document_id": doc_id,
        "enable_rl": True,  # Use RL optimization
        "max_retries": 3
    }
)
test_session_id = response.json()["session_id"]

# Check test progress
response = requests.get(
    f"http://localhost:8000/api/v1/tests/{test_session_id}/status"
)
print(response.json())
```

### Example 2: Query Test Results

```python
# Get comprehensive test report
response = requests.get(
    f"http://localhost:8000/api/v1/tests/{test_session_id}/report"
)
report = response.json()

print(f"Total APIs: {report['total_endpoints']}")
print(f"Passed: {report['passed']}")
print(f"Failed: {report['failed']}")
print(f"Coverage: {report['coverage_percentage']}%")
```

## 🎓 How It Works

### 1. Document Analysis Phase
```
PDF/JSON Upload → LlamaParse Extraction → Semantic Chunking → ChromaDB Storage
```

### 2. Endpoint Discovery Phase
```
LLM Analysis → Extract API Endpoints → Identify Dependencies → Build Execution Graph
```

### 3. Test Generation Phase
```
RAG Retrieval → Context Assembly → LLM Test Case Generation → Payload Creation
```

### 4. Intelligent Execution Phase
```
RL Agent Selects Next API → Execute Test → Success? → Store in Flow DB
                                       ↓ Failure
                           Error Analysis → LLM Fixes Payload → Retry (max 3x)
```

### 5. Learning Phase
```
Test Results → RL Reward Calculation → Policy Update → Improved Future Testing
```

## 🔬 Reinforcement Learning

### Training RL Agent

```bash
# Start RL training service
docker-compose --profile training up rl_trainer

# Monitor training progress
docker-compose logs -f rl_trainer
```

### RL Metrics

- **State**: Tested APIs, auth status, dependencies, coverage
- **Action**: Choose next API to test + test variation type
- **Reward**: Coverage increase + bugs found + efficiency
- **Algorithm**: PPO with curiosity-driven exploration

## 📈 Roadmap

- [x] Docker infrastructure
- [ ] Document parsing module
- [ ] Dual ChromaDB RAG system
- [ ] Multi-agent LLM orchestration
- [ ] Test execution engine
- [ ] Basic RL agent (Q-Learning)
- [ ] Advanced RL (PPO with curiosity)
- [ ] FastAPI endpoints
- [ ] Web dashboard (optional)

## 🐛 Troubleshooting

### ChromaDB Connection Issues

```bash
# Restart ChromaDB
docker-compose restart chromadb

# Check ChromaDB logs
docker-compose logs chromadb
```

### Celery Workers Not Processing Tasks

```bash
# Check Redis connection
docker-compose exec api redis-cli -h redis ping

# Restart workers
docker-compose restart celery_worker
```

### Out of Memory

```bash
# Increase Docker memory limit (Docker Desktop)
# Settings → Resources → Memory → Increase to 8GB+

# Or reduce parallelization
# In .env: MAX_PARALLEL_TESTS=2
```

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md

## 📧 Support

For issues and questions:
- GitHub Issues: [Create Issue](https://github.com/yourrepo/issues)
- Documentation: [Wiki](https://github.com/yourrepo/wiki)

---

**Built with 2025 State-of-the-Art AI Technologies**
- Meta's TestGen-LLM & ACH approaches
- DeepREST RL methodology
- LlamaParse document understanding
- RAG best practices from 2025 research
