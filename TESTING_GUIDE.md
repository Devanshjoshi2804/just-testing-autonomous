# Testing Guide - Real API Documentation

Complete guide for testing your AutoTest-RL system with real API documentation.

---

## Quick Start

### 1. Start the System

```bash
# Start all services
docker compose up -d

# Check services are running
docker compose ps

# View logs
docker compose logs -f
```

**Services started:**
- ✅ FastAPI backend (port 8000)
- ✅ Ollama LLM server (port 11434)
- ✅ ChromaDB vector database (port 8001)
- ✅ Redis task queue (port 6379)
- ✅ Celery workers (background processing)
- ✅ Flower monitoring (port 5555)

### 2. Add Your API Documentation

Place your files in `docs/api-specs/`:

```bash
# For OpenAPI specs
cp your-api-spec.yaml docs/api-specs/

# For PDF documentation
cp your-api-docs.pdf docs/api-specs/
```

**Supported formats:**
- PDF (`.pdf`)
- OpenAPI JSON (`.json`)
- OpenAPI YAML (`.yaml`, `.yml`)

### 3. Run the Test Pipeline

```bash
# Test all documentation
python test_real_apis.py
```

This will:
1. **Discover** all docs in `docs/api-specs/`
2. **Parse** each document to extract API structure
3. **Extract** constraints and validation rules
4. **Generate** comprehensive test cases
5. **Save** results to `data/test-results/` and `data/parsed-docs/`

---

## What You'll See

### Sample Output:

```
================================================================================
AutoTest-RL: Real API Testing
================================================================================

Discovering API documentation...
Found 3 documentation files:
  - 1 PDF files
  - 1 JSON files
  - 1 YAML files

================================================================================
Testing: sample-users-api.yaml
================================================================================
Step 1: Parsing document...
  ✅ Parsed 5 endpoints

Step 2: Extracting constraints...
  ✅ Extracted 24 constraints

Step 3: Generating tests...
  ✅ Generated 247 tests

================================================================================
TEST SUMMARY
================================================================================

Total documents tested: 3
  ✅ Success: 3
  ❌ Failed: 0

Success rate: 100.0%

================================================================================
SUCCESSFUL TESTS
================================================================================

✅ sample-users-api.yaml
   parsing: {'status': 'success', 'endpoints_found': 5, 'pages': 0}
   constraint_extraction: {'status': 'success', 'constraints_found': 24}
   test_generation: {'status': 'success', 'tests_generated': 247}

📄 Full report saved to: data/test-results/test_report_20250118_143052.json
```

---

## Generated Output Files

After running tests, check these directories:

### 1. Test Results (`data/test-results/`)

**test_report_YYYYMMDD_HHMMSS.json**
```json
{
  "timestamp": "2025-01-18T14:30:52.123456",
  "tests": [
    {
      "file": "docs/api-specs/sample-users-api.yaml",
      "file_name": "sample-users-api.yaml",
      "file_type": ".yaml",
      "status": "success",
      "steps": {
        "parsing": {
          "status": "success",
          "endpoints_found": 5,
          "pages": 0
        },
        "constraint_extraction": {
          "status": "success",
          "constraints_found": 24
        },
        "test_generation": {
          "status": "success",
          "tests_generated": 247
        }
      }
    }
  ],
  "summary": {
    "total": 1,
    "success": 1,
    "failed": 0
  }
}
```

### 2. Parsed Documentation (`data/parsed-docs/`)

**{filename}_parsed.json** - Extracted API structure
```json
{
  "endpoints": [
    {
      "path": "/users",
      "method": "GET",
      "description": "Retrieves a paginated list of users",
      "parameters": {
        "page": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 1
        },
        "limit": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 20
        }
      },
      "responses": {
        "200": { "description": "Successful response" },
        "401": { "description": "Unauthorized" }
      }
    }
  ]
}
```

**{filename}_constraints.json** - Extracted constraints
```json
{
  "GET /users": {
    "page": {
      "type": "integer",
      "minimum": 1,
      "maximum": 1000
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    }
  }
}
```

**{filename}_tests.json** - Generated test cases
```json
[
  {
    "endpoint": "/users",
    "method": "GET",
    "type": "positive",
    "strategy": "happy_path",
    "test_case": "List users with valid pagination",
    "parameters": {
      "page": 1,
      "limit": 20
    },
    "expected_status": 200
  },
  {
    "endpoint": "/users",
    "method": "GET",
    "type": "negative",
    "strategy": "boundary_value",
    "test_case": "Page number below minimum",
    "parameters": {
      "page": 0,
      "limit": 20
    },
    "expected_status": 422
  }
]
```

---

## Test Strategies Applied

For each endpoint, the system generates tests using:

### 1. **Happy Path Tests** (Positive)
- Valid requests with typical data
- Expected to succeed (200, 201, 204)

### 2. **Boundary Value Tests**
- Minimum values (e.g., `page=1`)
- Maximum values (e.g., `page=1000`)
- Just below minimum (e.g., `page=0`)
- Just above maximum (e.g., `page=1001`)

### 3. **Negative Tests**
- Missing required fields
- Invalid data types
- Out-of-range values
- Invalid formats

### 4. **Combinatorial Tests**
- Test parameter combinations
- 2-way and 3-way coverage
- Interaction testing

### 5. **Security Tests (OWASP)**
- SQL injection payloads
- XSS attempts
- Command injection
- Path traversal
- Authentication bypass attempts

### 6. **Error Scenario Tests**
- Documented error conditions
- Expected error responses
- Error message quality validation

### 7. **Schema Validation**
- Response matches OpenAPI schema
- Required fields present
- Type validation
- Format validation

---

## Expected Test Counts

Based on endpoint complexity:

| Endpoint Type | Parameters | Expected Tests |
|--------------|------------|----------------|
| Simple GET | 0-2 | 10-20 |
| GET with filters | 3-5 | 30-50 |
| POST/PUT | 5-8 fields | 50-80 |
| Complex CRUD | 10+ fields | 100-150 |

**Example: sample-users-api.yaml (5 endpoints)**
- `GET /users` → 45 tests
- `POST /users` → 62 tests
- `GET /users/{id}` → 38 tests
- `PUT /users/{id}` → 58 tests
- `DELETE /users/{id}` → 22 tests
- `POST /users/{id}/password` → 22 tests
- **Total: 247 tests**

---

## Sample API Included

The system includes `docs/api-specs/sample-users-api.yaml` with:

**5 Endpoints:**
1. `GET /users` - List users with pagination
2. `POST /users` - Create new user
3. `GET /users/{userId}` - Get user by ID
4. `PUT /users/{userId}` - Update user
5. `DELETE /users/{userId}` - Delete user
6. `POST /users/{userId}/password` - Change password

**Features demonstrated:**
- ✅ Query parameters with constraints
- ✅ Path parameters (UUID format)
- ✅ Request body validation
- ✅ Multiple response codes
- ✅ Authentication requirements
- ✅ Error response schemas
- ✅ Field formats (email, uuid, date-time)
- ✅ Enum constraints
- ✅ Min/max length and value constraints

---

## Testing Your Own APIs

### Step 1: Prepare Documentation

**For OpenAPI Specs:**
- Use OpenAPI 3.0.x or Swagger 2.0
- Include detailed parameter descriptions
- Define all constraints (min, max, format, enum)
- Document all response codes
- Include example values

**For PDF Documentation:**
- Ensure text is machine-readable (not scanned images)
- Use clear section headers
- Include endpoint paths and methods
- List parameters with types and constraints
- Document error codes and messages

### Step 2: Run Initial Test

```bash
# Test single file first
python test_real_apis.py
```

Check the output for:
- ✅ Endpoints found
- ✅ Constraints extracted
- ✅ Tests generated

### Step 3: Review Generated Tests

```bash
# View parsed structure
cat data/parsed-docs/your-api_parsed.json | jq .

# View constraints
cat data/parsed-docs/your-api_constraints.json | jq .

# View generated tests
cat data/parsed-docs/your-api_tests.json | jq . | head -50
```

### Step 4: Improve Documentation

If tests are incomplete, enhance your documentation with:
- More detailed constraints
- Example values
- Error scenarios
- Validation rules

Then re-run the test script.

---

## Troubleshooting

### Problem: No endpoints found

**Possible causes:**
- PDF is scanned image (not text)
- OpenAPI spec has incorrect format
- File is empty or corrupted

**Solutions:**
- Convert PDF to text-based format
- Validate OpenAPI spec: https://editor.swagger.io/
- Check file encoding (should be UTF-8)

### Problem: Few tests generated

**Possible causes:**
- Missing constraint definitions
- No parameter documentation
- Minimal error scenarios

**Solutions:**
- Add min/max constraints
- Define field formats (email, uuid, etc.)
- Document validation rules
- List all response codes

### Problem: Parsing errors

**Check:**
```bash
# View full error details
python test_real_apis.py 2>&1 | tee test-output.log

# Check if services are running
docker compose ps

# View service logs
docker compose logs ollama
docker compose logs chromadb
```

**Common fixes:**
- Restart services: `docker compose restart`
- Pull latest models: `docker compose up ollama_loader`
- Check disk space: `df -h`

### Problem: Out of memory

**If parsing large PDFs:**
```bash
# Increase Docker memory limits
docker compose down
# Edit docker-compose.yml and add memory limits
docker compose up -d
```

---

## Advanced Usage

### Testing Specific Files

Modify `test_real_apis.py`:
```python
# Test only specific file
docs = [Path("docs/api-specs/your-api.yaml")]
```

### Custom Test Generation

```python
# Add your own test strategies
from src.generation.enhanced_test_generator import EnhancedTestGenerator

generator = EnhancedTestGenerator(settings=settings)
tests = await generator.generate_comprehensive_tests(
    endpoint=endpoint,
    constraints=constraints,
    strategies=['boundary_value', 'security']  # Only these strategies
)
```

### Integration with TestRunner

```python
from src.executors.test_runner import TestRunner

# Load parsed data and tests
with open('data/parsed-docs/your-api_tests.json') as f:
    tests = json.load(f)

# Execute tests against real API
runner = TestRunner(settings=settings)
results = await runner.run_tests(
    tests=tests,
    base_url="https://api.example.com",
    auth_token="your-token"
)
```

---

## Next Steps

### Phase 6: Testing & Quality (Recommended Next)

The backend roadmap suggests these priorities:

**Immediate (Week 1-2):**
1. ✅ Test with real API docs (YOU ARE HERE)
2. ⬜ Write unit tests for components
3. ⬜ Add integration tests
4. ⬜ Set up CI/CD pipeline

**Short term (Week 3-4):**
5. ⬜ Add database persistence (PostgreSQL)
6. ⬜ Implement caching layer (Redis)
7. ⬜ Add performance benchmarks

**Medium term (Month 2-3):**
8. ⬜ OAuth/SAML authentication support
9. ⬜ Advanced RL algorithm (PPO)
10. ⬜ Prometheus metrics and monitoring

See `BACKEND_ENHANCEMENT_ROADMAP.md` for complete plan.

---

## Summary Checklist

- [ ] Docker services running (`docker compose ps`)
- [ ] API documentation added to `docs/api-specs/`
- [ ] Test script executed (`python test_real_apis.py`)
- [ ] Results reviewed in `data/test-results/`
- [ ] Generated tests reviewed in `data/parsed-docs/`
- [ ] Coverage gaps identified
- [ ] Documentation improved for better test coverage

---

## Getting Help

**Check logs:**
```bash
# Application logs
tail -f logs/app.log

# Service logs
docker compose logs -f api
docker compose logs -f ollama
docker compose logs -f celery_worker
```

**Validate setup:**
```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs

# Celery monitoring
open http://localhost:5555
```

**Common issues:** See `BRUTAL_REALITY_CHECK.md` and `BACKEND_ENHANCEMENT_ROADMAP.md`

---

**You're now ready to test AutoTest-RL with real API documentation!**

Start with the included `sample-users-api.yaml`, then add your own documentation step by step.
