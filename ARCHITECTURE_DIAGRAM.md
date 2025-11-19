# 🏗️ AutoTest-RL Architecture Diagrams

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER / CLIENT                                      │
│                     (Browser, curl, Postman, etc.)                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTP/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI APPLICATION (Port 8000)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Middleware Stack                              │   │
│  │  Request ID → Security → Audit → Rate Limit → Logging → Compression │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────┬──────────────┬──────────────┬──────────────────────┐    │
│  │  Documents   │    Tests     │  Intelligence │      Metrics         │    │
│  │   Routes     │   Routes     │    Routes     │      Routes          │    │
│  └──────────────┴──────────────┴──────────────┴──────────────────────┘    │
└────────┬────────────────┬────────────────┬────────────────┬────────────────┘
         │                │                │                │
         ▼                ▼                ▼                ▼
┌────────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│     REDIS      │ │  CHROMADB   │ │   OLLAMA     │ │  POSTGRES    │
│  (Port 6379)   │ │ (Port 8001) │ │ (Port 11434) │ │ (Optional)   │
│                │ │             │ │              │ │              │
│ • Task Queue   │ │ • Doc Store │ │ • Phi-3.5    │ │ • Sessions   │
│ • Cache        │ │ • Flow Store│ │ • Llama 3.2  │ │ • Results    │
│ • Rate Limit   │ │ • Embeddings│ │ • Local LLM  │ │ • Endpoints  │
└────────┬───────┘ └──────┬──────┘ └──────┬───────┘ └──────────────┘
         │                │                │
         ▼                │                │
┌────────────────────────┐│                │
│   CELERY WORKERS       ││                │
│                        ││                │
│ ┌──────────────────┐  ││                │
│ │ Document Parser  │◄─┼┼────────────────┘
│ │ • LlamaParse     │  ││
│ │ • PDF/JSON       │  ││
│ └──────────────────┘  ││
│                        ││
│ ┌──────────────────┐  ││
│ │  Test Executor   │◄─┼┘
│ │ • Parallel Run   │  │
│ │ • Self-Healing   │  │
│ └──────────────────┘  │
│                        │
│ ┌──────────────────┐  │
│ │   RL Trainer     │  │
│ │ • Q-Learning     │  │
│ │ • Optimization   │  │
│ └──────────────────┘  │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│   CELERY BEAT          │
│ (Periodic Scheduler)   │
│                        │
│ • Model Retraining     │
│ • Cache Cleanup        │
│ • Health Checks        │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│      FLOWER            │
│   (Port 5555)          │
│                        │
│ • Task Monitor         │
│ • Worker Status        │
│ • Task History         │
└────────────────────────┘
```

---

## 🔄 Complete Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DOCUMENT UPLOAD                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │  POST /api/v1/documents/upload │
                    │  • File: API_Documentation.pdf │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: DOCUMENT PARSING                            │
│                                                                           │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐          │
│  │  LlamaParse  │─────▶│  PyMuPDF     │─────▶│ Raw Text     │          │
│  │  (Cloud API) │      │  (Fallback)  │      │ Extraction   │          │
│  └──────────────┘      └──────────────┘      └──────┬───────┘          │
│                                                      │                   │
│                                                      ▼                   │
│                                            ┌──────────────────┐         │
│                                            │ Endpoint Analyzer│         │
│                                            │ • Regex patterns │         │
│                                            │ • LLM analysis   │         │
│                                            └────────┬─────────┘         │
│                                                     │                    │
│                                                     ▼                    │
│                                          ┌────────────────────┐         │
│                                          │ Endpoints Found:   │         │
│                                          │ • POST /users      │         │
│                                          │ • GET /users/{id}  │         │
│                                          │ • PUT /users/{id}  │         │
│                                          │ • DELETE /users/{id}│        │
│                                          └────────┬───────────┘         │
└──────────────────────────────────────────────────┼─────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: TEXT CHUNKING                              │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  DocumentChunker                                                  │   │
│  │  • Chunk size: 2000 characters                                    │   │
│  │  • Overlap: 400 characters                                        │   │
│  │  • Preserve context across chunks                                │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Chunks Created:                                                 │   │
│  │  Chunk 1: "The API allows you to manage users..."               │   │
│  │  Chunk 2: "To create a user, send POST to /users..."            │   │
│  │  Chunk 3: "Authentication requires Bearer token..."             │   │
│  │  Chunk 4: "User object contains: id, name, email..."            │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: EMBEDDING GENERATION                         │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Sentence Transformers (all-MiniLM-L6-v2)                        │   │
│  │  • Local model (no API calls)                                    │   │
│  │  • 384-dimensional vectors                                       │   │
│  │  • Fast inference (~50ms per chunk)                              │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Embeddings:                                                     │   │
│  │  Chunk 1: [0.23, -0.45, 0.67, 0.12, ..., -0.34] (384 dims)     │   │
│  │  Chunk 2: [0.11, 0.56, -0.23, 0.89, ..., 0.45]  (384 dims)     │   │
│  │  Chunk 3: [-0.34, 0.12, 0.78, -0.56, ..., 0.23] (384 dims)     │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 5: CHROMADB STORAGE                            │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  ChromaDB Collection: "doc_12345"                                │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Document ID  │  Text Chunk  │  Embedding  │  Metadata    │ │   │
│  │  ├────────────────────────────────────────────────────────────┤ │   │
│  │  │  doc_0        │  "The API..." │  [0.23,...] │  {page: 1}  │ │   │
│  │  │  doc_1        │  "To create..." │ [0.11,...] │  {page: 2}  │ │   │
│  │  │  doc_2        │  "Auth req..." │ [-0.34,...] │  {page: 3}  │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  PHASE 6: CONSTRAINT EXTRACTION                          │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  ConstraintExtractor                                             │   │
│  │  • Analyzes parameter descriptions                              │   │
│  │  • Extracts validation rules                                    │   │
│  │  • Identifies data types, ranges, patterns                      │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Constraints Found:                                              │   │
│  │  POST /users:                                                    │   │
│  │    • name: string, required, min_length=2, max_length=50        │   │
│  │    • email: string, required, format=email                      │   │
│  │    • age: integer, optional, min=0, max=150                     │   │
│  │    • role: enum["admin", "user", "guest"], default="user"       │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 PHASE 7: DEPENDENCY GRAPH                                │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  DependencyGraph                                                 │   │
│  │  • Identifies CRUD chains                                        │   │
│  │  • Finds data flow patterns                                      │   │
│  │  • Determines execution order                                    │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Dependency Graph:                                               │   │
│  │                                                                  │   │
│  │  POST /users ──────┐                                            │   │
│  │       │            │                                            │   │
│  │       │ (user_id)  │                                            │   │
│  │       ▼            │                                            │   │
│  │  GET /users/{id}   │                                            │   │
│  │       │            │                                            │   │
│  │       ▼            │                                            │   │
│  │  PUT /users/{id}   │                                            │   │
│  │       │            │                                            │   │
│  │       ▼            │                                            │   │
│  │  DELETE /users/{id}◄┘                                           │   │
│  │                                                                  │   │
│  │  CRUD Chain: Create → Read → Update → Delete                   │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 8: TEST GENERATION                              │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  RAG Query: "How to create a user?"                             │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  1. Generate query embedding                               │ │   │
│  │  │  2. Search ChromaDB for similar chunks                     │ │   │
│  │  │  3. Retrieve top 5 relevant chunks                         │ │   │
│  │  │  4. Assemble context                                       │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LLM Generation (Ollama - Phi-3.5)                               │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Prompt:                                                   │ │   │
│  │  │  "Based on this documentation, generate a test case        │ │   │
│  │  │   for creating a user. Include valid test data."          │ │   │
│  │  │                                                            │ │   │
│  │  │  Context: [Retrieved chunks about user creation]          │ │   │
│  │  │                                                            │ │   │
│  │  │  Response:                                                 │ │   │
│  │  │  {                                                         │ │   │
│  │  │    "method": "POST",                                       │ │   │
│  │  │    "path": "/users",                                       │ │   │
│  │  │    "headers": {"Authorization": "Bearer token"},          │ │   │
│  │  │    "body": {                                               │ │   │
│  │  │      "name": "John Doe",                                   │ │   │
│  │  │      "email": "john@example.com",                          │ │   │
│  │  │      "age": 30,                                            │ │   │
│  │  │      "role": "user"                                        │ │   │
│  │  │    },                                                      │ │   │
│  │  │    "expected_status": 201                                 │ │   │
│  │  │  }                                                         │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  MutationTestGenerator (Security Tests)                          │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Generate 40+ mutation tests:                              │ │   │
│  │  │  • SQL Injection: {"name": "'; DROP TABLE users--"}       │ │   │
│  │  │  • XSS: {"name": "<script>alert('xss')</script>"}         │ │   │
│  │  │  • Oversized: {"name": "A" * 10000}                       │ │   │
│  │  │  • Invalid email: {"email": "not-an-email"}               │ │   │
│  │  │  • Negative age: {"age": -5}                              │ │   │
│  │  │  • Missing required: {"name": "John"} (no email)          │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 9: RL PRIORITIZATION                            │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  TestOptimizer (Q-Learning)                                      │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  For each endpoint:                                        │ │   │
│  │  │  1. Build state vector:                                    │ │   │
│  │  │     - endpoint_hash                                        │ │   │
│  │  │     - hour_of_day = 10                                     │ │   │
│  │  │     - day_of_week = 3 (Wednesday)                          │ │   │
│  │  │     - days_since_change = 2                                │ │   │
│  │  │     - recent_failure_rate = 15%                            │ │   │
│  │  │     - dependency_health = 90%                              │ │   │
│  │  │                                                            │ │   │
│  │  │  2. Query Q-table for best action                         │ │   │
│  │  │  3. Choose priority: CRITICAL/HIGH/NORMAL/LOW/SKIP        │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Prioritized Test Queue:                                         │   │
│  │  🔴 CRITICAL: POST /users (creates data, high failure rate)     │   │
│  │  🟠 HIGH: GET /users/{id} (depends on POST)                     │   │
│  │  🟡 NORMAL: PUT /users/{id} (standard priority)                 │   │
│  │  🟢 LOW: DELETE /users/{id} (cleanup, low priority)             │   │
│  │  ⏭️  SKIP: GET /health (stable, tested recently)                │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   PHASE 10: TEST EXECUTION                               │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  TestRunner (Parallel Execution)                                 │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Test 1: POST /users                                       │ │   │
│  │  │  ├─ Execute HTTP request                                   │ │   │
│  │  │  ├─ Status: 201 Created ✓                                  │ │   │
│  │  │  ├─ Extract: user_id = "12345"                             │ │   │
│  │  │  └─ Store in FlowStore for next test                       │ │   │
│  │  │                                                            │ │   │
│  │  │  Test 2: GET /users/12345                                  │ │   │
│  │  │  ├─ Use user_id from Test 1                                │ │   │
│  │  │  ├─ Execute HTTP request                                   │ │   │
│  │  │  ├─ Status: 200 OK ✓                                       │ │   │
│  │  │  └─ Validate response schema                               │ │   │
│  │  │                                                            │ │   │
│  │  │  Test 3: PUT /users/12345                                  │ │   │
│  │  │  ├─ Execute HTTP request                                   │ │   │
│  │  │  ├─ Status: 400 Bad Request ✗                              │ │   │
│  │  │  ├─ Error: "Missing required field: carrier"               │ │   │
│  │  │  └─ Trigger Self-Healing                                   │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Self-Healing (ErrorFixer)                                       │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  1. Analyze error: "Missing required field: carrier"      │ │   │
│  │  │  2. Query RAG: "What fields are required for PUT /users?" │ │   │
│  │  │  3. LLM suggests: Add "carrier" field                     │ │   │
│  │  │  4. Retry with fixed payload:                             │ │   │
│  │  │     {                                                      │ │   │
│  │  │       "name": "John Updated",                             │ │   │
│  │  │       "carrier": "default_carrier"  ← Added               │ │   │
│  │  │     }                                                      │ │   │
│  │  │  5. Status: 200 OK ✓                                      │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PHASE 11: RL LEARNING                                │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Reward Calculation                                              │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  POST /users (CRITICAL priority):                         │ │   │
│  │  │  • Result: SUCCESS                                         │ │   │
│  │  │  • Reward: +20 (found it works, high priority)            │ │   │
│  │  │                                                            │ │   │
│  │  │  GET /users/{id} (HIGH priority):                         │ │   │
│  │  │  • Result: SUCCESS                                         │ │   │
│  │  │  • Reward: +15 (correct prioritization)                   │ │   │
│  │  │                                                            │ │   │
│  │  │  PUT /users/{id} (NORMAL priority):                       │ │   │
│  │  │  • Result: FAILED → HEALED → SUCCESS                      │ │   │
│  │  │  • Reward: +5 (found issue, needed healing)               │ │   │
│  │  │                                                            │ │   │
│  │  │  DELETE /users/{id} (LOW priority):                       │ │   │
│  │  │  • Result: SUCCESS                                         │ │   │
│  │  │  • Reward: +3 (correct low priority)                      │ │   │
│  │  │                                                            │ │   │
│  │  │  GET /health (SKIP):                                       │ │   │
│  │  │  • Result: SKIPPED (was stable)                           │ │   │
│  │  │  • Reward: +10 (saved time)                               │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Q-Table Update                                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Q(state, action) ← Q + α[r + γ max Q(s',a') - Q]         │ │   │
│  │  │                                                            │ │   │
│  │  │  Q(POST /users, CRITICAL) = 0.65 → 0.72                   │ │   │
│  │  │  Q(GET /users/{id}, HIGH) = 0.58 → 0.64                   │ │   │
│  │  │  Q(GET /health, SKIP) = 0.81 → 0.85                       │ │   │
│  │  │                                                            │ │   │
│  │  │  Epsilon decay: 0.10 → 0.0995 (explore less over time)    │ │   │
│  │  │  Save Q-table to: data/rl_models/q_table.pkl              │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 12: REPORTING                                 │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Test Results Summary                                            │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  Total Tests: 45                                           │ │   │
│  │  │  Passed: 42 (93.3%)                                        │ │   │
│  │  │  Failed: 3 (6.7%)                                          │ │   │
│  │  │  Self-Healing Actions: 1                                   │ │   │
│  │  │                                                            │ │   │
│  │  │  Coverage:                                                 │ │   │
│  │  │  • Endpoint Coverage: 100% (5/5 endpoints)                │ │   │
│  │  │  • Status Code Coverage: 80% (4/5 common codes)           │ │   │
│  │  │  • CRUD Coverage: 100% (1/1 chains)                       │ │   │
│  │  │                                                            │ │   │
│  │  │  Performance:                                              │ │   │
│  │  │  • Total Duration: 12.5s                                  │ │   │
│  │  │  • Avg Test Time: 278ms                                   │ │   │
│  │  │  • Time Saved by RL: 5.2s                                 │ │   │
│  │  │                                                            │ │   │
│  │  │  Issues Found:                                             │ │   │
│  │  │  • Missing "carrier" field validation                     │ │   │
│  │  │  • SQL injection vulnerability in name field              │ │   │
│  │  │  • XSS vulnerability in email field                       │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 RAG (Retrieval Augmented Generation) Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER QUERY                                    │
│              "How do I authenticate?"                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: QUERY EMBEDDING                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Sentence Transformer                                     │  │
│  │  "authenticate" → [0.45, -0.23, 0.67, ..., 0.12]        │  │
│  │  (384-dimensional vector)                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 2: SEMANTIC SEARCH IN CHROMADB                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Cosine Similarity Search                                 │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Query Vector: [0.45, -0.23, 0.67, ...]            │ │  │
│  │  │  vs                                                 │ │  │
│  │  │  All Document Vectors in ChromaDB                  │ │  │
│  │  │                                                     │ │  │
│  │  │  Calculate: cosine_similarity(query, doc)          │ │  │
│  │  │  Filter: similarity > 0.7                          │ │  │
│  │  │  Return: Top 5 most similar chunks                 │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 3: RETRIEVED CHUNKS                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Chunk 1 (similarity: 0.92):                             │  │
│  │  "Authentication is done via Bearer token in the         │  │
│  │   Authorization header. Obtain token from /auth/login"   │  │
│  │                                                           │  │
│  │  Chunk 2 (similarity: 0.88):                             │  │
│  │  "To authenticate, include: Authorization: Bearer        │  │
│  │   YOUR_TOKEN in all API requests"                        │  │
│  │                                                           │  │
│  │  Chunk 3 (similarity: 0.85):                             │  │
│  │  "Login endpoint: POST /auth/login with username and     │  │
│  │   password. Returns access_token valid for 24 hours"     │  │
│  │                                                           │  │
│  │  Chunk 4 (similarity: 0.79):                             │  │
│  │  "Token format: JWT with claims: user_id, role, exp"     │  │
│  │                                                           │  │
│  │  Chunk 5 (similarity: 0.75):                             │  │
│  │  "Unauthorized requests return 401 with error message"   │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 4: CONTEXT ASSEMBLY                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Combine retrieved chunks into coherent context:          │  │
│  │                                                           │  │
│  │  CONTEXT:                                                 │  │
│  │  """                                                      │  │
│  │  Authentication is done via Bearer token in the          │  │
│  │  Authorization header. To authenticate, include:         │  │
│  │  Authorization: Bearer YOUR_TOKEN in all API requests.   │  │
│  │                                                           │  │
│  │  To obtain a token, use the login endpoint:              │  │
│  │  POST /auth/login with username and password.            │  │
│  │  Returns access_token valid for 24 hours.                │  │
│  │                                                           │  │
│  │  Token format: JWT with claims: user_id, role, exp.      │  │
│  │  Unauthorized requests return 401 with error message.    │  │
│  │  """                                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 5: LLM GENERATION                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Ollama (Phi-3.5 3.8B)                                    │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  PROMPT:                                            │ │  │
│  │  │  "Based on this API documentation, generate a       │ │  │
│  │  │   test case for authentication.                     │ │  │
│  │  │                                                      │ │  │
│  │  │   DOCUMENTATION:                                    │ │  │
│  │  │   [Context from Step 4]                             │ │  │
│  │  │                                                      │ │  │
│  │  │   Generate a complete test case with:               │ │  │
│  │  │   - Login request                                   │ │  │
│  │  │   - Token extraction                                │ │  │
│  │  │   - Authenticated request                           │ │  │
│  │  │   - Expected responses"                             │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  LLM RESPONSE:                                      │ │  │
│  │  │  {                                                  │ │  │
│  │  │    "test_name": "Authentication Flow",             │ │  │
│  │  │    "steps": [                                       │ │  │
│  │  │      {                                              │ │  │
│  │  │        "name": "Login",                             │ │  │
│  │  │        "method": "POST",                            │ │  │
│  │  │        "path": "/auth/login",                       │ │  │
│  │  │        "body": {                                    │ │  │
│  │  │          "username": "testuser",                    │ │  │
│  │  │          "password": "testpass123"                  │ │  │
│  │  │        },                                           │ │  │
│  │  │        "expected_status": 200,                      │ │  │
│  │  │        "extract": {                                 │ │  │
│  │  │          "token": "$.access_token"                  │ │  │
│  │  │        }                                            │ │  │
│  │  │      },                                             │ │  │
│  │  │      {                                              │ │  │
│  │  │        "name": "Authenticated Request",             │ │  │
│  │  │        "method": "GET",                             │ │  │
│  │  │        "path": "/users/me",                         │ │  │
│  │  │        "headers": {                                 │ │  │
│  │  │          "Authorization": "Bearer {{token}}"        │ │  │
│  │  │        },                                           │ │  │
│  │  │        "expected_status": 200                       │ │  │
│  │  │      }                                              │ │  │
│  │  │    ]                                                │ │  │
│  │  │  }                                                  │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                STEP 6: RETURN TEST CASE                          │
│              (Ready for execution)                               │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight**: RAG allows the LLM to generate accurate tests based on YOUR specific API documentation, without needing to be retrained!

---

## 🧠 Reinforcement Learning Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  ENDPOINT TO TEST                                │
│              GET /users/{id}/orders                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              BUILD STATE VECTOR                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  StateBuilder.build_state()                               │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  endpoint_hash: hash("GET /users/{id}/orders")     │ │  │
│  │  │  hour_of_day: 14 (2 PM)                            │ │  │
│  │  │  day_of_week: 3 (Wednesday)                        │ │  │
│  │  │  days_since_change: 5 (last modified 5 days ago)   │ │  │
│  │  │  recent_failure_rate: 25% (failed 1/4 recent runs) │ │  │
│  │  │  dependency_health: 80% (parent endpoints stable)  │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                                                           │  │
│  │  State Tuple: (hash_12345, 14, 3, 5, 25, 80)            │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              QUERY Q-TABLE                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Q-Table Lookup:                                          │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Q(state, CRITICAL) = 0.65                          │ │  │
│  │  │  Q(state, HIGH)     = 0.72  ← Highest!             │ │  │
│  │  │  Q(state, NORMAL)   = 0.58                          │ │  │
│  │  │  Q(state, LOW)      = 0.45                          │ │  │
│  │  │  Q(state, SKIP)     = 0.30                          │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           ε-GREEDY ACTION SELECTION                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Epsilon (ε) = 0.10 (10% exploration)                     │  │
│  │  Random number = 0.75                                     │  │
│  │                                                           │  │
│  │  if random < ε:                                           │  │
│  │      # Explore: Choose random action                      │  │
│  │      action = random.choice([CRITICAL, HIGH, ...])        │  │
│  │  else:                                                    │  │
│  │      # Exploit: Choose best action from Q-table           │  │
│  │      action = argmax(Q-values)  # HIGH                    │  │
│  │                                                           │  │
│  │  Since 0.75 > 0.10:                                       │  │
│  │  → EXPLOIT: Choose HIGH (Q = 0.72)                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                EXECUTE TEST                                      │
│  🟠 HIGH PRIORITY: GET /users/{id}/orders                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              TEST RESULT                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Status: 200 OK                                           │  │
│  │  Success: True                                            │  │
│  │  Duration: 245ms                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           CALCULATE REWARD                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Action: HIGH                                             │  │
│  │  Result: SUCCESS                                          │  │
│  │  Failure Rate: 25% (moderately unstable)                 │  │
│  │                                                           │  │
│  │  Reward Logic:                                            │  │
│  │  • HIGH priority + SUCCESS = Good prioritization          │  │
│  │  • Endpoint had 25% failure rate (was risky)             │  │
│  │  • Testing it was valuable                               │  │
│  │                                                           │  │
│  │  Reward: +15 (FOUND_FAILURE_HIGH bonus)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              UPDATE Q-VALUE                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Q-Learning Update Rule:                                  │  │
│  │  Q(s,a) ← Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]       │  │
│  │                                                           │  │
│  │  Where:                                                   │  │
│  │  • s = current state                                      │  │
│  │  • a = action taken (HIGH)                                │  │
│  │  • r = reward received (+15)                              │  │
│  │  • s' = next state                                        │  │
│  │  • α = learning rate (0.1)                                │  │
│  │  • γ = discount factor (0.9)                              │  │
│  │                                                           │  │
│  │  Calculation:                                             │  │
│  │  current_Q = 0.72                                         │  │
│  │  max_next_Q = 0.68 (best action in next state)           │  │
│  │  new_Q = 0.72 + 0.1 * [15 + 0.9 * 0.68 - 0.72]          │  │
│  │        = 0.72 + 0.1 * [15.612 - 0.72]                    │  │
│  │        = 0.72 + 1.489                                     │  │
│  │        = 2.209                                            │  │
│  │                                                           │  │
│  │  Q(state, HIGH) = 0.72 → 2.21 ✓ (Improved!)             │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              PERSIST Q-TABLE                                     │
│  Save to: data/rl_models/q_table.pkl                            │
│  Q-table size: 1,247 state-action pairs                         │
└─────────────────────────────────────────────────────────────────┘
```

**Over Time**: The agent learns which endpoints need HIGH priority (unstable, critical) and which can be SKIPPED (stable, low value).

---

## 📊 System Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                  AUTOTEST-RL METRICS                             │
│                  (Real-time Dashboard)                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  API PERFORMANCE                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Request Rate:        245 req/min                         │  │
│  │  Avg Response Time:   123ms                               │  │
│  │  P95 Latency:         456ms                               │  │
│  │  P99 Latency:         892ms                               │  │
│  │  Error Rate:          0.2%                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CACHE PERFORMANCE                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Hit Rate:            87.3%                               │  │
│  │  Miss Rate:           12.7%                               │  │
│  │  Avg Hit Latency:     2ms                                 │  │
│  │  Avg Miss Latency:    145ms                               │  │
│  │  Total Keys:          12,456                              │  │
│  │  Memory Used:         234 MB / 512 MB                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LLM PERFORMANCE                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Model:               Phi-3.5 (3.8B)                      │  │
│  │  Avg Inference Time:  287ms                               │  │
│  │  Tokens/sec:          45                                  │  │
│  │  Total Inferences:    1,234                               │  │
│  │  Cache Hit Rate:      62%                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TEST EXECUTION                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Total Tests Run:     45,678                              │  │
│  │  Success Rate:        94.2%                               │  │
│  │  Avg Test Duration:   234ms                               │  │
│  │  Tests/hour:          3,456                               │  │
│  │  Healing Actions:     127                                 │  │
│  │  Healing Success:     89.8%                               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  REINFORCEMENT LEARNING                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Q-Table Size:        1,247 entries                       │  │
│  │  Exploration Rate:    0.095 (9.5%)                        │  │
│  │  Avg Episode Reward:  +23.4                               │  │
│  │  Time Saved:          127 minutes (total)                 │  │
│  │  Failures Caught:     89                                  │  │
│  │  Failures Missed:     2 (critical!)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CELERY WORKERS                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Active Workers:      4                                   │  │
│  │  Active Tasks:        12                                  │  │
│  │  Pending Tasks:       3                                   │  │
│  │  Completed Today:     1,234                               │  │
│  │  Failed Today:        5                                   │  │
│  │  Avg Task Duration:   4.5s                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  CHROMADB                                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Collections:         3                                   │  │
│  │  Total Documents:     12,456                              │  │
│  │  Total Embeddings:    12,456 × 384 dims                   │  │
│  │  Disk Usage:          1.2 GB                              │  │
│  │  Avg Query Time:      45ms                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

**This document provides a complete visual understanding of the AutoTest-RL system architecture and data flows!** 🚀

