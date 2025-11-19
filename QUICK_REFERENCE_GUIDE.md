# ⚡ Quick Reference Guide - AutoTest-RL

## 📚 Documentation Index

### 🎯 Start Here (New Users)
1. **[UNDERSTANDING_SUMMARY.md](UNDERSTANDING_SUMMARY.md)** - High-level overview (READ THIS FIRST!)
2. **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
3. **[README.md](README.md)** - Project overview

### 🔍 Deep Dive (Technical Understanding)
4. **[COMPLETE_SYSTEM_ANALYSIS.md](COMPLETE_SYSTEM_ANALYSIS.md)** - Complete technical analysis
5. **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Visual architecture diagrams
6. **[FOLDER_STRUCTURE_GUIDE.md](FOLDER_STRUCTURE_GUIDE.md)** - Detailed folder structure

### 🛠️ Usage Guides
7. **[API_USAGE.md](API_USAGE.md)** - API endpoint usage examples
8. **[DOCKER_COMMANDS.md](DOCKER_COMMANDS.md)** - Docker commands reference
9. **[CELERY_USAGE.md](CELERY_USAGE.md)** - Celery task queue usage
10. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing guide

---

## 🐳 Docker Containers (Running)

### Your Current Setup
Based on your screenshot, you have **5 containers running**:

| Container | Port | Status | Purpose |
|-----------|------|--------|---------|
| **api** | 8000 | ✅ Running | FastAPI backend |
| **redis** | 6379 | ✅ Running | Cache & task queue |
| **ollama** | 11434 | ✅ Running | Local LLM server |
| **chromadb** | 8001 | ✅ Running | Vector database |
| **ollama_loader** | - | ⏭️ Exited | Model downloader (one-time) |

### Quick Container Commands

```bash
# View all containers
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f api
docker-compose logs -f redis
docker-compose logs -f ollama

# Restart a service
docker-compose restart api

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

---

## 🌐 Access Points

### Web Interfaces
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **API Alternative (ReDoc)**: http://localhost:8000/redoc
- **Flower (Celery Monitor)**: http://localhost:5555
- **ChromaDB**: http://localhost:8001

### Health Checks
- **Basic Health**: http://localhost:8000/health
- **Detailed Health**: http://localhost:8000/health/detailed
- **Readiness**: http://localhost:8000/health/ready
- **Liveness**: http://localhost:8000/health/live

### API Endpoints
```bash
# Upload document
POST http://localhost:8000/api/v1/documents/upload

# Start tests
POST http://localhost:8000/api/v1/tests/start

# Check test status
GET http://localhost:8000/api/v1/tests/{session_id}/status

# Get test results
GET http://localhost:8000/api/v1/tests/{session_id}/results
```

---

## 📁 Key Files & Folders

### Configuration
```
.env                    # Environment variables (API keys)
docker-compose.yml      # Container orchestration
requirements.txt        # Python dependencies
src/config.py          # Application configuration
```

### Source Code (Most Important)
```
src/api/main.py                      # FastAPI application entry point
src/workflow/workflow_orchestrator.py # Complete testing pipeline
src/rag/doc_store.py                 # RAG system (semantic search)
src/rl/test_optimizer.py             # Reinforcement learning agent
src/agents/test_generator.py         # AI test generation
src/agents/error_fixer.py            # Self-healing
```

### Data Storage
```
data/doc_chroma_db/     # Document embeddings
data/flow_chroma_db/    # Test execution history
data/rl_models/         # RL model checkpoints
logs/                   # Application logs
results/                # Test results
uploads/                # Uploaded documents
```

---

## 🚀 Common Tasks

### 1. Upload API Documentation
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@your-api-doc.pdf"
```

**Response:**
```json
{
  "document_id": "doc_12345",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

### 2. Start Testing
```bash
curl -X POST http://localhost:8000/api/v1/tests/start \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_12345",
    "base_url": "https://api.example.com",
    "enable_rl": true,
    "comprehensive_mode": true
  }'
```

**Response:**
```json
{
  "session_id": "session_67890",
  "status": "running",
  "message": "Test execution started"
}
```

### 3. Check Test Status
```bash
curl http://localhost:8000/api/v1/tests/session_67890/status
```

**Response:**
```json
{
  "session_id": "session_67890",
  "status": "running",
  "progress": 65,
  "tests_completed": 29,
  "tests_total": 45
}
```

### 4. Get Test Results
```bash
curl http://localhost:8000/api/v1/tests/session_67890/results
```

**Response:**
```json
{
  "session_id": "session_67890",
  "status": "completed",
  "total_tests": 45,
  "passed": 42,
  "failed": 3,
  "success_rate": 93.3,
  "coverage": {
    "endpoint_coverage": 100,
    "status_code_coverage": 80
  }
}
```

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# LLM Configuration
LLM_PROVIDER=ollama              # ollama | openai | anthropic | groq
LLM_MODEL=phi3.5:3.8b            # Local model
FAST_LLM_MODEL=llama3.2:3b       # Faster model

# API Keys (Optional - for cloud LLMs)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...

# Database
CHROMA_HOST=chromadb
CHROMA_PORT=8001
REDIS_HOST=redis
REDIS_PORT=6379

# Security
REQUIRE_AUTH=true
MASTER_API_KEY=your-secret-key

# Performance
MAX_PARALLEL_TESTS=5
MAX_RETRIES=3
```

---

## 🧠 Key Concepts (Quick Explanation)

### RAG (Retrieval Augmented Generation)
```
Problem: LLMs don't know your specific API docs
Solution: Store docs in vector DB, retrieve relevant chunks, give to LLM
Result: Accurate tests based on actual documentation
```

### Reinforcement Learning (Q-Learning)
```
Problem: Which tests should run first?
Solution: Agent learns from experience (rewards/penalties)
Result: Smart prioritization, time savings
```

### Self-Healing
```
Problem: Tests fail when APIs change
Solution: Analyze error, query docs, LLM suggests fix, retry
Result: Fewer false failures, automatic adaptation
```

### Dependency Graph
```
Problem: Tests depend on each other (need user_id to create order)
Solution: Map dependencies, execute in correct order
Result: Realistic workflows, integration testing
```

---

## 📊 System Architecture (Simplified)

```
USER
 ↓
API (FastAPI) ←→ Redis (Cache)
 ↓
Celery Worker
 ↓
┌─────────────┬─────────────┬─────────────┐
│   Ollama    │  ChromaDB   │  Database   │
│   (LLM)     │  (RAG)      │  (Results)  │
└─────────────┴─────────────┴─────────────┘
```

**Flow:**
1. User uploads PDF → API
2. API → Celery task (parse document)
3. Celery → Ollama (LLM analysis)
4. Celery → ChromaDB (store embeddings)
5. Celery → Test generation (RAG + LLM)
6. Celery → Test execution (RL prioritization)
7. Celery → Database (store results)
8. API → User (return results)

---

## 🎯 What Each Component Does

### **API (FastAPI)**
- Receives HTTP requests
- Triggers background tasks
- Returns results
- Health checks

### **Redis**
- Caches responses
- Stores Celery task queue
- Rate limiting
- Session storage

### **Ollama**
- Runs AI models locally
- Generates test cases
- Analyzes documentation
- Fixes failed tests

### **ChromaDB**
- Stores document embeddings
- Enables semantic search
- Tracks test history

### **Celery**
- Background task processing
- Document parsing
- Test execution
- Report generation

---

## 🔍 Troubleshooting

### Container Not Starting
```bash
# Check logs
docker-compose logs [service_name]

# Restart service
docker-compose restart [service_name]

# Rebuild and restart
docker-compose up -d --build [service_name]
```

### API Not Responding
```bash
# Check health
curl http://localhost:8000/health

# Check logs
docker-compose logs -f api

# Restart API
docker-compose restart api
```

### Tests Failing
```bash
# Check Celery logs
docker-compose logs -f celery_worker

# Check Flower dashboard
http://localhost:5555

# Check test results
curl http://localhost:8000/api/v1/tests/{session_id}/results
```

### ChromaDB Issues
```bash
# Check ChromaDB logs
docker-compose logs -f chromadb

# Restart ChromaDB
docker-compose restart chromadb

# Clear ChromaDB data (WARNING: deletes all data)
rm -rf data/doc_chroma_db/*
rm -rf data/flow_chroma_db/*
```

### Ollama Issues
```bash
# Check Ollama logs
docker-compose logs -f ollama

# Check models
curl http://localhost:11434/api/tags

# Pull model manually
docker-compose exec ollama ollama pull phi3.5:3.8b
```

---

## 📈 Performance Tips

### 1. Increase Parallelization
```bash
# In .env
MAX_PARALLEL_TESTS=10  # Default: 5
```

### 2. Use Faster Model
```bash
# In .env
LLM_MODEL=llama3.2:3b  # Faster than phi3.5:3.8b
```

### 3. Enable Caching
```bash
# Already enabled by default
# Cache TTLs:
# - Health checks: 5-10s
# - Document parsing: 1 hour
# - Test suites: 30 minutes
```

### 4. Scale Celery Workers
```bash
# Scale to 4 workers
docker-compose up -d --scale celery_worker=4
```

---

## 🔐 Security

### API Authentication
```bash
# Enable in .env
REQUIRE_AUTH=true
MASTER_API_KEY=your-secret-key

# All requests need header:
X-API-Key: your-secret-key
```

### Rate Limiting
```bash
# Enabled by default
DEFAULT_RATE_LIMIT=100  # req/min
RATE_LIMIT_UPLOAD=10    # req/min
RATE_LIMIT_TEST_START=20  # req/min
```

---

## 📚 Further Reading

### Technical Deep Dives
- **[COMPLETE_SYSTEM_ANALYSIS.md](COMPLETE_SYSTEM_ANALYSIS.md)** - Complete technical analysis
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Visual diagrams
- **[FOLDER_STRUCTURE_GUIDE.md](FOLDER_STRUCTURE_GUIDE.md)** - Folder structure

### Implementation Details
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md)** - Implementation details
- **[MODULE_DEPENDENCY_MAP.md](MODULE_DEPENDENCY_MAP.md)** - Module dependencies

### Project Status
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current project status
- **[REALISTIC_PROGRESS.md](REALISTIC_PROGRESS.md)** - Progress report

---

## 🎓 Learning Path

### Beginner (Understanding)
1. Read **[UNDERSTANDING_SUMMARY.md](UNDERSTANDING_SUMMARY.md)**
2. Read **[QUICKSTART.md](QUICKSTART.md)**
3. Try uploading a document
4. Review results

### Intermediate (Usage)
1. Read **[API_USAGE.md](API_USAGE.md)**
2. Read **[DOCKER_COMMANDS.md](DOCKER_COMMANDS.md)**
3. Experiment with different configurations
4. Monitor via Flower dashboard

### Advanced (Development)
1. Read **[COMPLETE_SYSTEM_ANALYSIS.md](COMPLETE_SYSTEM_ANALYSIS.md)**
2. Read **[FOLDER_STRUCTURE_GUIDE.md](FOLDER_STRUCTURE_GUIDE.md)**
3. Explore source code in `src/`
4. Run tests: `pytest tests/ -v`
5. Contribute improvements

---

## 🆘 Getting Help

### Documentation
- Check relevant `.md` files in project root
- Read inline code comments
- Review API documentation at `/docs`

### Logs
```bash
# Application logs
docker-compose logs -f api

# Celery logs
docker-compose logs -f celery_worker

# All logs
docker-compose logs -f
```

### Health Checks
```bash
# Basic health
curl http://localhost:8000/health

# Detailed health (checks all dependencies)
curl http://localhost:8000/health/detailed
```

### Monitoring
- **Flower**: http://localhost:5555 (Celery tasks)
- **Swagger**: http://localhost:8000/docs (API endpoints)

---

## ✅ Quick Checklist

### System Running?
- [ ] All containers running: `docker-compose ps`
- [ ] API healthy: `curl http://localhost:8000/health`
- [ ] Redis connected: `docker-compose logs redis`
- [ ] Ollama ready: `curl http://localhost:11434/api/tags`
- [ ] ChromaDB accessible: `curl http://localhost:8001`

### Ready to Test?
- [ ] Document uploaded
- [ ] Base URL configured
- [ ] API keys set (if using cloud LLMs)
- [ ] Authentication configured
- [ ] Celery workers running

### Results Available?
- [ ] Test execution completed
- [ ] Results endpoint accessible
- [ ] Coverage metrics calculated
- [ ] Issues identified
- [ ] Recommendations provided

---

## 🎯 Summary

**AutoTest-RL** is an intelligent API testing system that:
- ✅ Uses AI to understand documentation
- ✅ Generates comprehensive test cases
- ✅ Learns optimal testing strategy (RL)
- ✅ Self-heals broken tests
- ✅ Runs locally (no cloud dependency)
- ✅ Provides detailed reports

**Key Technologies:**
- FastAPI, Celery, Redis, ChromaDB, Ollama
- LangChain, Stable Baselines3, Sentence Transformers
- Docker, SQLAlchemy, Loguru

**Main Benefits:**
- 🚀 Fast: Local LLM, parallel execution
- 🔒 Secure: Local processing, no data sent to cloud
- 💰 Cost-effective: No API costs
- 🧠 Smart: RL optimization, self-healing
- 📊 Comprehensive: 45+ tests per endpoint

---

**For more information, see the documentation files listed at the top of this guide!** 📚

