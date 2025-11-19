# AI Agent Instructions for AutoTest-RL

## Project Overview
**AutoTest-RL** is an enterprise-grade intelligent API testing system that uses AI agents, RAG (Retrieval-Augmented Generation), and Reinforcement Learning to automatically test APIs with zero manual test writing. The system analyzes API documentation, generates comprehensive tests (43+ per endpoint vs. 3 traditional), detects security vulnerabilities, and self-heals when APIs change.

**Key Innovation**: Combines semantic understanding (natural language + schemas), multi-agent LLM orchestration, security mutation testing (OWASP Top 10), self-healing, and Q-Learning optimization for intelligent test prioritization.

## Architecture: 8-Phase Workflow Pipeline

### Phase 1: Document Processing (`src/parsers/`)
- **Enhanced Parser** (`enhanced_document_parser.py`): Parses PDF/JSON/YAML docs with semantic analysis
- **Semantic Analyzer** (`src/analysis/semantic_doc_analyzer.py`): Extracts use cases, examples, business rules, error patterns from prose
- **Text Chunking** (`text_splitter.py`): Splits docs for RAG (2000 chars, 400 overlap)
- **Output**: `DocumentationContext` objects with 16 semantic fields per endpoint

### Phase 2: Dual RAG System (`src/rag/`)
- **Document Store** (`doc_store.py`): Permanent ChromaDB collection for API documentation
- **Flow Store** (`flow_store.py`): Session-based ChromaDB for test execution state (requests/responses)
- **Why Dual?**: Flow Store enables context-aware testing by retrieving auth tokens, IDs from previous API calls
- **Embeddings**: Mistral embeddings via Ollama

### Phase 3: Multi-Agent Analysis (`src/agents/`)
- **EndpointAnalyzer** (`endpoint_analyzer.py`): Extracts endpoints, auth, params using fast LLM (Phi-3.5 Mini)
- **TestGenerator** (`test_generator.py`): Generates test payloads using RAG + Flow context
- **ErrorFixer** (`error_fixer.py`): Analyzes failures, proposes fixes, retries (max 3)
- **Pattern**: All agents inherit from `BaseAgent` with common LLM interaction logic

### Phase 4: Dependency Analysis (`src/workflow/`)
- **DependencyGraph** (`dependency_graph.py`): Builds endpoint dependencies (e.g., POST /users before GET /users/{id})
- **DataFlowTracker** (`data_flow_tracker.py`): Tracks ID extractions, token passing between APIs
- **WorkflowOrchestrator** (`workflow_orchestrator.py`): Coordinates end-to-end execution (8 phases)
- **Output**: CRUD chains, workflow sequences, execution order

### Phase 5: Comprehensive Test Generation (`src/testing/`)
**3 parallel strategies** generate 43+ tests per endpoint:

1. **Semantic Tests** (`semantic_test_generator.py`) - 16 tests from docs:
   - Golden tests (from curl examples)
   - Scenario tests (from use cases)
   - Validation tests (from best practices)
   - Negative tests (from common errors)
   - Boundary tests (from edge cases)
   - Constraint tests (from business rules)

2. **Mutation Tests** (`mutation_test_generator.py`) - 24 security tests:
   - 19 attack patterns: SQL injection, XSS, command injection, SSRF, etc.
   - 3 payloads per pattern
   - OWASP Top 10 coverage (19 CWEs, 150+ payloads)

3. **LLM Tests** (`test_generator.py`) - 3 AI-generated variations:
   - Positive, negative, boundary cases
   - Uses RAG for context

**Test Prioritization**: Sort by (1) source (golden→security→LLM), (2) severity (CRITICAL→LOW), (3) confidence (HIGH→LOW)

### Phase 6: RL-Optimized Execution (`src/rl/`)
- **TestOptimizer** (`test_optimizer.py`): Q-Learning agent prioritizes test execution
- **State**: endpoint_hash, hour_of_day, days_since_change, failure_rate, dependency_health
- **Actions**: [critical, high, normal, low, skip] - may skip stable endpoints
- **Rewards**: +20 found failure, +10 correct skip, -50 missed failure
- **Learning**: Persists Q-table to JSON, improves over ~10 runs

### Phase 7: Self-Healing (`src/analysis/change_detector.py`, `src/testing/test_healer.py`)
- **Change Detection**: Compares expected vs actual responses
- **Severity Classification**: BREAKING (field removed), NON_BREAKING (field added), MINOR (status code)
- **Auto-Healing**: Updates tests if no BREAKING changes (adds fields, updates status codes)
- **Tracking**: Logs all healing actions to history

### Phase 8: Advanced Reporting (`src/reporting/advanced_reporter.py`)
- **4 formats**: JSON, Markdown, HTML, Plain Text
- **Metrics**: Coverage quality, dependency chains, security findings, RL progress, healing actions
- **Grades**: Overall grade A-F based on success rate, security, self-healing

## Critical Developer Workflows

### Quick Start (5 minutes)
```bash
# 1. Start all services (8 containers)
docker-compose up -d

# 2. Wait for Ollama models (first time: ~5 min, downloads Phi-3.5 Mini & Llama 3.2 3B)
docker-compose logs -f ollama_loader

# 3. Run end-to-end demo (Pet Store API example)
docker-compose exec api python demo_end_to_end_workflow.py

# 4. Test API endpoints
docker-compose exec api python test_api_endpoints.py
```

### Makefile Commands (30+ utilities in `Makefile`)
```bash
make up              # Start services
make down            # Stop services  
make logs            # View API logs
make shell           # Enter API container shell
make test            # Run pytest suite (28+ unit tests)
make clean           # Clean volumes and restart
```

### Key Docker Services (8 containers)
- `api` (port 8000): FastAPI backend with hot reload (`src/` volume-mounted)
- `ollama` (port 11434): Local LLM server (Phi-3.5 Mini, Llama 3.2 3B)
- `chromadb` (port 8001): Vector database for RAG
- `redis` (port 6379): Cache & Celery broker
- `celery_worker`: Background task processing
- `celery_beat`: Periodic tasks
- `flower` (port 5555): Celery monitoring dashboard
- `ollama_loader`: Auto-downloads models on startup (runs once)

### Running Tests
```bash
# Unit tests (28+ tests with pytest fixtures)
docker-compose exec api pytest tests/unit/ -v

# Integration tests (end-to-end workflow)
docker-compose exec api pytest tests/integration/ -v

# With coverage (70% threshold)
docker-compose exec api pytest --cov=src --cov-report=html

# Specific test markers (defined in pytest.ini)
docker-compose exec api pytest -m security  # Security tests
docker-compose exec api pytest -m e2e       # End-to-end tests
```

## Project-Specific Conventions

### Module Organization Pattern
```
src/
├── agents/          # LLM agents (analyzer, generator, fixer)
├── analysis/        # Semantic analysis, constraint extraction, change detection
├── api/             # FastAPI routes, middleware (auth, rate limit, metrics)
├── rag/             # Dual ChromaDB stores (doc + flow)
├── testing/         # Test generators (semantic, mutation, healing)
├── workflow/        # Orchestration, dependency graphs, data flow
├── rl/              # Q-Learning optimizer, state builder, rewards
├── reporting/       # Multi-format report generation
├── observability/   # Prometheus metrics (35+), distributed tracing
├── parsers/         # Document parsing (PDF/JSON/YAML)
├── executors/       # HTTP test execution engine
└── config.py        # Pydantic settings (364 lines)
```

### Async/Await Everywhere
- **All I/O operations are async**: HTTP requests (`httpx.AsyncClient`), LLM calls, database queries
- **FastAPI routes**: Use `async def` for endpoints
- **Test execution**: `asyncio.gather()` for parallel execution
- **Pattern**: Never block the event loop with synchronous I/O

### Configuration Management (`src/config.py`)
- **Pydantic Settings**: Type-safe environment variables with validation
- **Multi-provider LLM**: Switch between Ollama (local), OpenAI, Anthropic, Groq via `LLM_PROVIDER`
- **Defaults favor local**: Ollama enabled by default (no API costs)
- **Key settings**:
  - `LLM_MODEL`: Model name (default: `llama3.2:3b`)
  - `CHUNK_SIZE`: RAG chunking (2000 chars)
  - `RAG_TOP_K`: Documents retrieved (5)
  - `RL_EPSILON`: Exploration rate (0.1)

### Error Handling Pattern
- **Custom exceptions** (`src/exceptions.py`): `AutoTestException` hierarchy
- **Middleware**: `error_handler.py` catches exceptions, returns structured JSON
- **Logging**: Loguru with correlation IDs for request tracing
- **Retry logic**: 3 attempts with AI-generated fixes via `ErrorFixer` agent

### Security & Production Features
- **Authentication** (`src/api/middleware/authentication.py`): API key-based with permissions
- **Rate Limiting** (`rate_limiter.py`): Redis-based sliding window (per-IP, per-key)
- **Input Validation** (`security.py`): XSS, SQL injection, path traversal prevention
- **Security Headers**: HSTS, CSP, X-Frame-Options via middleware
- **Observability** (`src/observability/`): 
  - 35+ Prometheus metrics (HTTP, business, LLM, RAG, RL)
  - Distributed tracing with spans and correlation IDs
  - Grafana dashboard (13 panels) in `grafana/dashboards/`

## Critical Integration Points

### LLM Communication Flow
```python
# Pattern used in all agents (src/agents/base_agent.py)
1. Build prompt with context
2. Query RAG stores for relevant docs/patterns
3. Call LLM via Ollama HTTP API (async)
4. Parse JSON response with retry
5. Store interaction in Flow Store for learning
```

### RAG Query Pattern
```python
# Document Store: Retrieve API docs
docs = await doc_store.query("How to authenticate?", top_k=5)

# Flow Store: Retrieve previous test data (e.g., auth token)
patterns = await flow_store.search_similar(
    query="authentication token from login",
    session_id="session_123"
)
```

### Workflow Orchestration Sequence (`WorkflowOrchestrator`)
```
1. Parse document → 2. Store in ChromaDB → 3. Extract constraints →
4. Build dependency graph → 5. Generate workflow sequences →
6. Generate tests (semantic+mutation+LLM) → 7. Execute with RL prioritization →
8. Generate reports (JSON/HTML/MD)
```

### Self-Healing Decision Tree
```
API response differs from expected
  ↓
Detect changes (ChangeDetector)
  ↓
Classify severity (BREAKING/NON_BREAKING/MINOR)
  ↓
Auto-heal if safe (TestHealer)
  - Add field: YES (non-breaking)
  - Remove field: NO (breaking, manual review)
  - Status code change: YES (minor)
  ↓
Log healing action
```

## Testing & Debugging

### Demo Scripts (Interactive Examples)
```bash
# Full workflow with Pet Store API
python demo_end_to_end_workflow.py

# Semantic analysis demonstration  
python demo_semantic_analysis.py

# Mutation testing showcase
python demo_mutation_testing.py

# RL optimization example
python demo_intelligent_testing.py

# Self-healing demo
python demo_self_healing.py
```

### Health Checks
```bash
# API health (checks Ollama, ChromaDB, Redis connectivity)
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics

# API documentation
open http://localhost:8000/docs  # Swagger UI
open http://localhost:8000/redoc # ReDoc
```

### Common Issues & Solutions

**Ollama models not loading**:
```bash
# Check ollama_loader logs (first startup takes 5-10 min)
docker-compose logs ollama_loader

# Manually trigger model download
docker exec autotest-ollama ollama pull phi3.5:3.8b
```

**ChromaDB connection failed**:
```bash
# Restart ChromaDB and clear data
docker-compose restart chromadb
rm -rf data/chroma_storage/*
```

**Tests failing with "No auth token"**:
```bash
# Flow Store needs authentication endpoint first
# Ensure endpoints are tested in dependency order
# Check DependencyGraph output in logs
```

**RL agent not learning**:
```bash
# Q-table persists to data/rl_models/q_table.pkl
# Delete to reset learning
rm data/rl_models/q_table.pkl

# Minimum 10 test runs for Q-values to converge
```

## Key Files for AI Agents

**Entry Points**:
- `src/api/main.py`: FastAPI app initialization, middleware setup
- `src/workflow/workflow_orchestrator.py`: End-to-end workflow coordination
- `demo_end_to_end_workflow.py`: Complete usage example

**Core Logic**:
- `src/testing/semantic_test_generator.py`: 14x test improvement over traditional
- `src/rl/test_optimizer.py`: Q-Learning implementation (405 lines)
- `src/analysis/change_detector.py`: Self-healing trigger logic
- `src/agents/test_generator.py`: RAG + LLM test generation

**Configuration**:
- `src/config.py`: All settings with docs (364 lines)
- `docker-compose.yml`: Service orchestration (8 containers)
- `.env.template`: Environment variables template
- `pytest.ini`: Test configuration with markers

**Documentation**:
- `README.md`: Complete system overview
- `ARCHITECTURE.md`: Detailed technical architecture (650 lines)
- `PROJECT_STATUS.md`: Current status, metrics, completed phases
- `API_USAGE.md`: REST API reference with examples
