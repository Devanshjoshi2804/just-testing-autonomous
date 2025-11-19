# 📁 Folder Structure Guide - AutoTest-RL

## 🎯 Quick Navigation

- [Root Directory](#root-directory)
- [src/ - Source Code](#src---source-code)
- [data/ - Persistent Data](#data---persistent-data)
- [tests/ - Test Suite](#tests---test-suite)
- [Configuration Files](#configuration-files)
- [Documentation](#documentation)

---

## 📂 Root Directory

```
just-testing-autonomous/
├── 🐳 docker-compose.yml          # Container orchestration
├── 🐳 Dockerfile                  # API container image
├── 📦 requirements.txt            # Python dependencies
├── 📦 requirements-test.txt       # Testing dependencies
├── 🔧 .env                        # Environment variables (API keys)
├── 🔧 .env.template               # Environment template
├── 📖 README.md                   # Project documentation
├── 📖 COMPLETE_SYSTEM_ANALYSIS.md # This analysis
├── 📖 ARCHITECTURE_DIAGRAM.md     # Visual diagrams
├── 📖 FOLDER_STRUCTURE_GUIDE.md   # This guide
├── 📝 pytest.ini                  # Pytest configuration
├── 📝 alembic.ini                 # Database migrations config
├── 🚀 start.sh                    # Startup script
├── 🚀 entrypoint.sh               # Docker entrypoint
├── 🛠️ Makefile                    # Build automation
├── 📊 coverage.xml                # Test coverage report
├── 📁 src/                        # Source code
├── 📁 tests/                      # Test suite
├── 📁 data/                       # Persistent data
├── 📁 logs/                       # Application logs
├── 📁 results/                    # Test results
├── 📁 uploads/                    # Uploaded documents
├── 📁 alembic/                    # Database migrations
├── 📁 scripts/                    # Utility scripts
├── 📁 benchmarks/                 # Performance benchmarks
├── 📁 docs/                       # Additional documentation
├── 📁 grafana/                    # Grafana dashboards
└── 📁 prometheus/                 # Prometheus config
```

---

## 📁 src/ - Source Code

### Overview
```
src/
├── __init__.py
├── config.py                      # Configuration management
├── exceptions.py                  # Custom exceptions
├── 📁 api/                        # FastAPI backend
├── 📁 agents/                     # AI agents
├── 📁 ai/                         # AI engine
├── 📁 analysis/                   # Analysis tools
├── 📁 cache/                      # Caching layer
├── 📁 database/                   # Data persistence
├── 📁 execution/                  # Test execution
├── 📁 executors/                  # Test runners
├── 📁 generators/                 # Test generators
├── 📁 ingestion/                  # Document ingestion
├── 📁 intelligence/               # AI coordination
├── 📁 learning/                   # Machine learning
├── 📁 llm/                        # LLM operations
├── 📁 metrics/                    # Metrics tracking
├── 📁 models/                     # Data models
├── 📁 observability/              # Monitoring
├── 📁 parsers/                    # Document parsers
├── 📁 rag/                        # RAG system
├── 📁 reporting/                  # Report generation
├── 📁 resilience/                 # Fault tolerance
├── 📁 rl/                         # Reinforcement learning
├── 📁 storage/                    # Storage backends
├── 📁 tasks/                      # Celery tasks
├── 📁 testing/                    # Testing utilities
├── 📁 utils/                      # Utility functions
├── 📁 validation/                 # Validation logic
└── 📁 workflow/                   # Workflow orchestration
```

---

### 📁 src/api/ - FastAPI Backend

**Purpose**: HTTP API server, routes, middleware

```
api/
├── __init__.py
├── main.py                        # FastAPI app, startup/shutdown
├── health.py                      # Health check endpoints
├── 📁 middleware/                 # HTTP middleware
│   ├── __init__.py
│   ├── authentication.py          # API key validation
│   ├── rate_limiter.py            # Rate limiting
│   ├── security.py                # Security headers
│   ├── logging_middleware.py      # Request/response logging
│   ├── cache.py                   # Response caching decorator
│   ├── compression.py             # Gzip compression
│   ├── error_handler.py           # Error handling
│   ├── metrics_middleware.py      # Prometheus metrics
│   └── request_id.py              # Request ID tracking
└── 📁 routes/                     # API endpoints
    ├── __init__.py
    ├── documents.py               # Document upload/management
    ├── tests.py                   # Test execution (sync)
    ├── tests_celery.py            # Test execution (async)
    ├── metrics.py                 # Monitoring metrics
    └── intelligence.py            # AI insights
```

**Key Files**:

#### `main.py` - FastAPI Application
```python
# What it does:
- Creates FastAPI app
- Registers middleware (order matters!)
- Includes routers
- Startup: Initialize Redis, DB, tracing
- Shutdown: Close connections gracefully
- Health checks: /health, /health/detailed, /health/ready, /health/live
```

#### `middleware/authentication.py` - API Key Auth
```python
# What it does:
- Validates X-API-Key header
- Checks against MASTER_API_KEY
- Returns 401 if invalid
- Skips auth for health endpoints
```

#### `middleware/rate_limiter.py` - Rate Limiting
```python
# What it does:
- Tracks requests per IP/API key
- Uses Redis for distributed rate limiting
- Different limits per endpoint:
  - Upload: 10 req/min
  - Test Start: 20 req/min
  - Auth: 5 req/min
  - Default: 100 req/min
- Returns 429 Too Many Requests if exceeded
```

#### `routes/documents.py` - Document Management
```python
# Endpoints:
POST /api/v1/documents/upload
  - Upload PDF/JSON API documentation
  - Triggers Celery task for parsing
  - Returns document_id

GET /api/v1/documents/{id}
  - Get document metadata
  - Returns parsing status, endpoints found

DELETE /api/v1/documents/{id}
  - Delete document and associated data
  - Cleans up ChromaDB collections
```

#### `routes/tests.py` - Test Execution
```python
# Endpoints:
POST /api/v1/tests/start
  - Start test execution
  - Triggers Celery task
  - Returns session_id

GET /api/v1/tests/{session_id}/status
  - Check test progress
  - Returns: pending/running/completed/failed

GET /api/v1/tests/{session_id}/results
  - Get test results
  - Returns: passed, failed, coverage, issues

GET /api/v1/tests/{session_id}/report
  - Get detailed report
  - Includes: coverage, performance, recommendations
```

---

### 📁 src/agents/ - AI Agents

**Purpose**: LLM-powered agents for specific tasks

```
agents/
├── __init__.py
├── base_agent.py                  # Base agent class
├── endpoint_analyzer.py           # Analyzes API endpoints
├── test_generator.py              # Generates test cases
├── enhanced_test_generator.py     # Advanced test generation
└── error_fixer.py                 # Self-healing agent
```

**Key Files**:

#### `endpoint_analyzer.py` - Endpoint Discovery
```python
# What it does:
class EndpointAnalyzer:
    def analyze_documentation(doc_text, base_url):
        # 1. Use regex to find endpoints:
        #    - POST /users
        #    - GET /users/{id}
        #    - PUT /users/{id}
        #    - DELETE /users/{id}
        
        # 2. Extract parameters:
        #    - Path params: {id}, {user_id}
        #    - Query params: ?page=1&limit=10
        #    - Body params: {"name": "...", "email": "..."}
        
        # 3. Identify authentication:
        #    - Bearer token
        #    - API key
        #    - Basic auth
        
        # 4. Find response formats:
        #    - JSON schema
        #    - Status codes
        
        # Returns: List of endpoint metadata
```

#### `test_generator.py` - Test Case Generation
```python
# What it does:
class TestGenerator:
    def generate_tests(endpoint, documentation):
        # 1. Query RAG for relevant documentation
        relevant_docs = rag.query(f"How to test {endpoint}")
        
        # 2. Build LLM prompt:
        prompt = f"""
        Generate test cases for:
        Endpoint: {endpoint}
        Documentation: {relevant_docs}
        
        Include:
        - Valid test data
        - Expected responses
        - Edge cases
        """
        
        # 3. LLM generates test cases
        tests = llm.generate(prompt)
        
        # 4. Validate and format tests
        return formatted_tests
```

#### `error_fixer.py` - Self-Healing
```python
# What it does:
class ErrorFixer:
    def fix_error(test_case, error_response):
        # 1. Analyze error message
        error_msg = error_response.json()["error"]
        
        # 2. Query RAG for solution
        solution = rag.query(f"How to fix: {error_msg}")
        
        # 3. LLM suggests fix
        prompt = f"""
        Test failed with: {error_msg}
        Documentation: {solution}
        Original test: {test_case}
        
        Suggest a fix:
        """
        
        fixed_test = llm.generate(prompt)
        
        # 4. Return fixed test case
        return fixed_test
```

---

### 📁 src/rag/ - RAG System

**Purpose**: Retrieval Augmented Generation for semantic search

```
rag/
├── __init__.py
├── doc_store.py                   # Document vector database
└── flow_store.py                  # Test flow history database
```

**Key Files**:

#### `doc_store.py` - Document Storage
```python
# What it does:
class DocumentStore:
    def __init__(collection_name="api_documentation"):
        # 1. Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./data/doc_chroma_db")
        
        # 2. Load sentence-transformers model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 3. Get or create collection
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def add_documents(texts, metadatas, ids):
        # 1. Generate embeddings (384-dim vectors)
        embeddings = self.model.encode(texts)
        
        # 2. Store in ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(query_text, n_results=5):
        # 1. Generate query embedding
        query_embedding = self.model.encode([query_text])[0]
        
        # 2. Semantic search (cosine similarity)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 3. Return relevant documents
        return results
```

**Why Two Stores?**
- **doc_store**: API documentation (static, rarely changes)
- **flow_store**: Test execution history (dynamic, frequently updated)

---

### 📁 src/rl/ - Reinforcement Learning

**Purpose**: Learn optimal test execution strategy

```
rl/
├── __init__.py
├── test_optimizer.py              # Q-Learning agent
├── state_builder.py               # Builds RL state vectors
└── reward_calculator.py           # Calculates rewards
```

**Key Files**:

#### `test_optimizer.py` - Q-Learning Agent
```python
# What it does:
class TestOptimizer:
    def __init__(alpha=0.1, gamma=0.9, epsilon=0.1):
        # Learning rate, discount factor, exploration rate
        self.q_table = {}  # {(state, action): Q-value}
    
    def choose_action(state):
        # ε-greedy policy
        if random() < epsilon:
            # Explore: random action
            return random.choice(['critical', 'high', 'normal', 'low', 'skip'])
        else:
            # Exploit: best known action
            q_values = {a: self.q_table.get((state, a), 0) for a in actions}
            return max(q_values, key=q_values.get)
    
    def update_q_value(state, action, reward, next_state):
        # Q-learning update rule
        current_q = self.q_table.get((state, action), 0)
        max_next_q = max(self.q_table.get((next_state, a), 0) for a in actions)
        
        new_q = current_q + alpha * (reward + gamma * max_next_q - current_q)
        
        self.q_table[(state, action)] = new_q
    
    def prioritize_endpoints(endpoints):
        # Assign priorities to all endpoints
        prioritized = []
        for endpoint in endpoints:
            state = StateBuilder.build_state(endpoint)
            action = self.choose_action(state)
            prioritized.append({**endpoint, 'priority': action})
        
        # Sort by priority
        return sorted(prioritized, key=lambda e: priority_order[e['priority']])
```

#### `state_builder.py` - State Vector Construction
```python
# What it does:
class StateBuilder:
    @staticmethod
    def build_state(endpoint, context):
        # Build state tuple from endpoint metadata
        return (
            hash(endpoint['path']),           # Unique endpoint ID
            datetime.now().hour,              # Hour of day (0-23)
            datetime.now().weekday(),         # Day of week (0-6)
            endpoint.get('days_since_change', 0),  # Code recency
            endpoint.get('failure_rate', 0),  # Historical reliability
            endpoint.get('dependency_health', 100)  # Related endpoints
        )
```

---

### 📁 src/workflow/ - Workflow Orchestration

**Purpose**: End-to-end pipeline coordination

```
workflow/
├── __init__.py
├── workflow_orchestrator.py       # Complete pipeline
├── dependency_graph.py            # Endpoint dependencies
├── data_flow_tracker.py           # Data flow between tests
├── state_transition_generator.py  # State transitions
├── state_transition_tester.py     # Test state transitions
└── state_machine_validator.py     # Validate state machines
```

**Key Files**:

#### `workflow_orchestrator.py` - End-to-End Pipeline
```python
# What it does:
class WorkflowOrchestrator:
    async def execute_complete_workflow(document_path, base_url):
        # Phase 1: Document Parsing
        parsed = await self._parse_document(document_path)
        
        # Phase 2: Storage in RAG
        await self._store_in_rag(parsed)
        
        # Phase 3: Analysis (constraints, semantic)
        constraints = await self._analyze_endpoints(parsed['endpoints'])
        
        # Phase 4: Dependency Graph
        graph = await self._build_dependency_graph(parsed['endpoints'])
        
        # Phase 5: Workflow Sequences
        workflows = await self._generate_workflow_sequences(graph)
        
        # Phase 6: Test Generation
        tests = await self._generate_tests(parsed['endpoints'], constraints)
        
        # Phase 7: Test Execution
        results = await self._execute_tests(tests, workflows)
        
        # Phase 8: Reporting
        report = await self._generate_reports(results)
        
        return report
```

#### `dependency_graph.py` - Endpoint Dependencies
```python
# What it does:
class DependencyGraph:
    def build_graph(endpoints):
        # 1. Identify CRUD resources
        #    POST /users → creates user_id
        #    GET /users/{id} → needs user_id
        
        # 2. Build dependency edges
        #    POST /users → GET /users/{id}
        #    POST /users → PUT /users/{id}
        #    POST /users → DELETE /users/{id}
        
        # 3. Find CRUD chains
        #    Create → Read → Update → Delete
        
        # 4. Determine execution order
        #    Must create before read/update/delete
```

---

### 📁 src/testing/ - Advanced Testing

**Purpose**: Specialized test generation strategies

```
testing/
├── __init__.py
├── semantic_test_generator.py     # Semantic analysis tests
├── mutation_test_generator.py     # Security mutation tests
├── role_based_scenario_generator.py  # Role-based tests
├── status_code_coverage_tracker.py   # HTTP status coverage
├── error_scenario_generator.py    # Error case generation
├── test_healer.py                 # Self-healing logic
└── security_patterns.py           # Security test patterns
```

**Key Files**:

#### `mutation_test_generator.py` - Security Tests
```python
# What it does:
class MutationTestGenerator:
    def generate_mutations(endpoint, parameter):
        mutations = []
        
        # SQL Injection
        mutations.append({"name": "'; DROP TABLE users--"})
        mutations.append({"name": "1' OR '1'='1"})
        
        # XSS
        mutations.append({"name": "<script>alert('xss')</script>"})
        mutations.append({"name": "<img src=x onerror=alert(1)>"})
        
        # Command Injection
        mutations.append({"name": "; ls -la"})
        mutations.append({"name": "| cat /etc/passwd"})
        
        # Path Traversal
        mutations.append({"file": "../../etc/passwd"})
        
        # Oversized Payloads
        mutations.append({"name": "A" * 10000})
        
        # Invalid Types
        mutations.append({"age": "not-a-number"})
        mutations.append({"email": "not-an-email"})
        
        # Boundary Values
        mutations.append({"age": -1})
        mutations.append({"age": 999999})
        
        return mutations
```

---

### 📁 src/database/ - Data Persistence

**Purpose**: SQLAlchemy models and repositories

```
database/
├── __init__.py
├── config.py                      # Database connection
├── models.py                      # SQLAlchemy models
└── 📁 repositories/               # Data access layer
    ├── __init__.py
    ├── test_session_repository.py # Test sessions
    ├── test_result_repository.py  # Test results
    ├── endpoint_repository.py     # Endpoints
    ├── coverage_repository.py     # Coverage metrics
    └── constraint_repository.py   # Constraints
```

**Database Schema**:
```sql
-- test_sessions
CREATE TABLE test_sessions (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR,
    status VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_tests INTEGER,
    passed INTEGER,
    failed INTEGER,
    success_rate FLOAT
);

-- test_results
CREATE TABLE test_results (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES test_sessions(id),
    endpoint VARCHAR,
    method VARCHAR,
    status_code INTEGER,
    success BOOLEAN,
    duration FLOAT,
    error_message TEXT,
    healing_applied BOOLEAN
);

-- endpoints
CREATE TABLE endpoints (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR,
    method VARCHAR,
    path VARCHAR,
    parameters JSONB,
    constraints JSONB
);

-- coverage
CREATE TABLE coverage (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR REFERENCES test_sessions(id),
    endpoint_coverage FLOAT,
    status_code_coverage FLOAT,
    crud_coverage FLOAT
);
```

---

### 📁 src/cache/ - Caching Layer

**Purpose**: Redis-backed caching for performance

```
cache/
├── __init__.py
├── redis_config.py                # Redis connection
├── cache_manager.py               # Cache operations
├── document_cache.py              # Document caching
├── test_suite_cache.py            # Test suite caching
└── constraint_cache.py            # Constraint caching
```

**What Gets Cached**:
```python
# Health checks (5-10s TTL)
@cached(ttl=5, key_prefix="health:basic")
async def health_check():
    return {"status": "healthy"}

# Document parsing (1 hour TTL)
@cached(ttl=3600, key_prefix="document:parsed")
async def parse_document(doc_id):
    return parsed_data

# Test suites (30 min TTL)
@cached(ttl=1800, key_prefix="test_suite")
async def get_test_suite(endpoint):
    return test_cases

# Constraints (1 hour TTL)
@cached(ttl=3600, key_prefix="constraints")
async def get_constraints(endpoint):
    return constraints
```

---

### 📁 src/observability/ - Monitoring

**Purpose**: Metrics, tracing, audit logging

```
observability/
├── __init__.py
├── metrics.py                     # Prometheus metrics
├── tracing.py                     # Distributed tracing
├── audit.py                       # Audit logging
└── sli_slo.py                     # SLI/SLO tracking
```

**Metrics Exposed**:
```python
# Prometheus metrics at :9090/metrics
http_requests_total{method="POST", endpoint="/api/v1/tests", status="200"}
http_request_duration_seconds{endpoint="/api/v1/tests"}
test_execution_duration_seconds{endpoint="POST /users"}
llm_inference_duration_seconds{model="phi3.5"}
cache_hit_rate{cache="redis"}
database_query_duration_seconds{table="test_results"}
celery_task_duration_seconds{task="parse_document"}
```

---

## 📁 data/ - Persistent Data

```
data/
├── 📁 chroma_storage/             # ChromaDB data
├── 📁 doc_chroma_db/              # Document embeddings
│   ├── chroma.sqlite3             # ChromaDB metadata
│   └── [UUID folders]             # Embedding vectors
├── 📁 flow_chroma_db/             # Test flow history
│   ├── chroma.sqlite3
│   └── [UUID folders]
└── 📁 rl_models/                  # RL model checkpoints
    ├── q_table.pkl                # Q-learning Q-table
    └── ppo_model.zip              # PPO model (if using)
```

**Data Persistence**:
- ChromaDB stores embeddings on disk
- RL models saved after each episode
- Survives container restarts
- Backed up via volume mounts

---

## 📁 tests/ - Test Suite

```
tests/
├── conftest.py                    # Pytest fixtures
├── 📁 unit/                       # Unit tests
│   ├── test_config.py
│   ├── test_document_parser.py
│   ├── test_endpoint_analyzer.py
│   ├── test_test_generator.py
│   ├── test_rl_optimizer.py
│   └── ...
└── 📁 integration/                # Integration tests
    ├── test_api_endpoints.py
    ├── test_workflow.py
    ├── test_rag_system.py
    └── ...
```

**Running Tests**:
```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test
pytest tests/unit/test_config.py::test_settings_validation -v
```

---

## 📝 Configuration Files

### `docker-compose.yml` - Container Orchestration
```yaml
# Defines 8 services:
- api: FastAPI backend
- ollama: Local LLM server
- ollama_loader: Model downloader
- chromadb: Vector database
- redis: Cache & task queue
- celery_worker: Background tasks
- celery_beat: Task scheduler
- flower: Celery monitoring
```

### `Dockerfile` - API Container
```dockerfile
# Multi-stage build:
1. Base: Python 3.11 slim
2. Dependencies: Install requirements
3. Final: Copy app, set permissions
```

### `requirements.txt` - Python Dependencies
```
# Key dependencies:
- fastapi: Web framework
- celery: Task queue
- chromadb: Vector database
- ollama: Local LLM
- langchain: LLM orchestration
- stable-baselines3: RL
- sentence-transformers: Embeddings
- sqlalchemy: ORM
- redis: Cache client
- loguru: Logging
```

### `.env` - Environment Variables
```bash
# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=phi3.5:3.8b
OLLAMA_BASE_URL=http://ollama:11434

# API Keys
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
```

---

## 📖 Documentation

```
Documentation/
├── README.md                      # Project overview
├── COMPLETE_SYSTEM_ANALYSIS.md    # Complete analysis
├── ARCHITECTURE_DIAGRAM.md        # Visual diagrams
├── FOLDER_STRUCTURE_GUIDE.md      # This guide
├── API_USAGE.md                   # API usage examples
├── QUICKSTART.md                  # Quick start guide
├── TESTING_GUIDE.md               # Testing guide
├── DOCKER_COMMANDS.md             # Docker commands
├── CELERY_USAGE.md                # Celery usage
└── docs/                          # Additional docs
    └── api-specs/                 # API specifications
        ├── openapi.yaml
        └── README.md
```

---

## 🎯 Key Takeaways

### Most Important Files
1. **src/config.py** - All configuration
2. **src/api/main.py** - API entry point
3. **src/workflow/workflow_orchestrator.py** - Complete pipeline
4. **src/rag/doc_store.py** - RAG system
5. **src/rl/test_optimizer.py** - RL agent
6. **docker-compose.yml** - Infrastructure

### Most Important Folders
1. **src/api/** - HTTP interface
2. **src/agents/** - AI agents
3. **src/rag/** - Semantic search
4. **src/rl/** - Reinforcement learning
5. **src/workflow/** - Pipeline orchestration
6. **src/testing/** - Test generation

### Data Flow Summary
```
Upload (src/api/routes/documents.py)
  ↓
Parse (src/parsers/enhanced_document_parser.py)
  ↓
Store (src/rag/doc_store.py)
  ↓
Analyze (src/agents/endpoint_analyzer.py)
  ↓
Generate Tests (src/agents/test_generator.py)
  ↓
Prioritize (src/rl/test_optimizer.py)
  ↓
Execute (src/executors/test_runner.py)
  ↓
Learn (src/rl/test_optimizer.py)
  ↓
Report (src/reporting/advanced_reporter.py)
```

---

**This guide provides a complete understanding of the folder structure and where to find everything!** 📁

