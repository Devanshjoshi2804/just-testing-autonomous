# AutoTest-RL API Usage Guide

Complete guide for using the REST API endpoints.

## Base URL

```
http://localhost:8000
```

## API Version

```
/api/v1
```

---

## 📄 Document Management Endpoints

### 1. Upload API Documentation

Upload PDF, JSON, or YAML API documentation for analysis.

**Endpoint:** `POST /api/v1/documents/upload`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@api_doc.pdf" \
  -F "name=My API Documentation" \
  -F "description=REST API for user management" \
  -F "base_url=https://api.example.com"
```

**Response:**
```json
{
  "document_id": "doc_abc123",
  "filename": "api_doc.pdf",
  "doc_type": "pdf",
  "file_size": 245632,
  "base_url": "https://api.example.com",
  "endpoints_found": 12,
  "chunks_created": 8,
  "uploaded_at": "2025-01-15T10:30:00Z"
}
```

---

### 2. List All Documents

Get list of all uploaded documents.

**Endpoint:** `GET /api/v1/documents/`

**Request:**
```bash
curl "http://localhost:8000/api/v1/documents/"
```

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_abc123",
      "filename": "api_doc.pdf",
      "name": "My API Documentation",
      "doc_type": "pdf",
      "file_size": 245632,
      "base_url": "https://api.example.com",
      "endpoints_count": 12,
      "uploaded_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### 3. Get Document Details

Get detailed information about a specific document.

**Endpoint:** `GET /api/v1/documents/{document_id}`

**Request:**
```bash
curl "http://localhost:8000/api/v1/documents/doc_abc123"
```

**Response:**
```json
{
  "id": "doc_abc123",
  "filename": "api_doc.pdf",
  "name": "My API Documentation",
  "description": "REST API for user management",
  "doc_type": "pdf",
  "file_size": 245632,
  "base_url": "https://api.example.com",
  "endpoints": [
    {
      "path": "/users",
      "method": "GET",
      "summary": "Get all users",
      "auth_required": false,
      "parameters": []
    },
    {
      "path": "/users",
      "method": "POST",
      "summary": "Create a new user",
      "auth_required": true,
      "parameters": [
        {"name": "username", "type": "string", "required": true},
        {"name": "email", "type": "string", "required": true}
      ]
    }
  ],
  "chunks_count": 8,
  "uploaded_at": "2025-01-15T10:30:00Z"
}
```

---

### 4. Delete Document

Delete a document and cleanup all associated data.

**Endpoint:** `DELETE /api/v1/documents/{document_id}`

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/doc_abc123"
```

**Response:**
```json
{
  "message": "Document deleted successfully",
  "document_id": "doc_abc123"
}
```

---

## 🧪 Test Execution Endpoints

### 5. Start Test Execution

Start intelligent API testing for a document.

**Endpoint:** `POST /api/v1/tests/start`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/tests/start" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_abc123",
    "max_retries": 3,
    "use_optimal_order": true,
    "test_types": ["positive"]
  }'
```

**Parameters:**
- `document_id` (required): Document ID to test
- `max_retries` (optional): Max retry attempts per endpoint (1-5, default: 3)
- `use_optimal_order` (optional): Use optimal testing order (default: true)
- `test_types` (optional): Test types to run (default: ["positive"])

**Response:**
```json
{
  "session_id": "session_xyz789",
  "document_id": "doc_abc123",
  "status": "pending",
  "total_endpoints": 12,
  "started_at": "2025-01-15T10:35:00Z",
  "estimated_duration": 60
}
```

---

### 6. Get Test Status

Get real-time status and progress of a test session.

**Endpoint:** `GET /api/v1/tests/{session_id}/status`

**Request:**
```bash
curl "http://localhost:8000/api/v1/tests/session_xyz789/status"
```

**Response:**
```json
{
  "session_id": "session_xyz789",
  "status": "processing",
  "progress": 58.3,
  "total_endpoints": 12,
  "tested_endpoints": 7,
  "passed": 6,
  "failed": 1,
  "started_at": "2025-01-15T10:35:00Z",
  "updated_at": "2025-01-15T10:36:30Z",
  "completed_at": null
}
```

**Status Values:**
- `pending`: Test session created, waiting to start
- `processing`: Tests currently running
- `completed`: All tests finished successfully
- `failed`: Test session encountered an error

---

### 7. Get Test Report

Get complete test results and detailed report (only available after completion).

**Endpoint:** `GET /api/v1/tests/{session_id}/report`

**Request:**
```bash
curl "http://localhost:8000/api/v1/tests/session_xyz789/report"
```

**Response:**
```json
{
  "session_id": "session_xyz789",
  "document_id": "doc_abc123",
  "status": "completed",
  "total_tests": 12,
  "passed": 10,
  "failed": 2,
  "success_rate": 83.3,
  "total_time": 45.6,
  "avg_time": 3.8,
  "total_attempts": 14,
  "started_at": "2025-01-15T10:35:00Z",
  "completed_at": "2025-01-15T10:36:15Z",
  "results": [
    {
      "endpoint": "GET /users",
      "method": "GET",
      "url": "https://api.example.com/users",
      "status_code": 200,
      "success": true,
      "attempts": 1,
      "elapsed_time": 1.2,
      "final_payload": {},
      "response": {
        "users": [{"id": 1, "name": "John"}]
      },
      "error": null
    },
    {
      "endpoint": "POST /users",
      "method": "POST",
      "url": "https://api.example.com/users",
      "status_code": 400,
      "success": false,
      "attempts": 3,
      "elapsed_time": 3.5,
      "final_payload": {
        "username": "testuser",
        "email": "test@example.com"
      },
      "response": {
        "error": "Email already exists"
      },
      "error": "Validation failed"
    }
  ],
  "flow_stats": {
    "requests": 14,
    "responses": 14,
    "successful_responses": 10
  }
}
```

---

### 8. List Test Sessions

Get list of all test sessions.

**Endpoint:** `GET /api/v1/tests/`

**Request:**
```bash
curl "http://localhost:8000/api/v1/tests/"
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_xyz789",
      "document_id": "doc_abc123",
      "status": "completed",
      "total_endpoints": 12,
      "tested_endpoints": 12,
      "passed": 10,
      "failed": 2,
      "started_at": "2025-01-15T10:35:00Z",
      "completed_at": "2025-01-15T10:36:15Z"
    }
  ],
  "total": 1
}
```

---

### 9. Delete Test Session

Delete a test session and cleanup resources.

**Endpoint:** `DELETE /api/v1/tests/{session_id}`

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/tests/session_xyz789"
```

**Response:**
```json
{
  "message": "Test session deleted successfully",
  "session_id": "session_xyz789"
}
```

---

## 🔧 Utility Endpoints

### Health Check

Check if the API is running.

**Endpoint:** `GET /health`

**Request:**
```bash
curl "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "0.1.0"
}
```

---

### Root Endpoint

Get API information.

**Endpoint:** `GET /`

**Request:**
```bash
curl "http://localhost:8000/"
```

**Response:**
```json
{
  "message": "AutoTest-RL API - Intelligent API Testing with Reinforcement Learning",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### API Info (Debug Mode Only)

Get detailed API configuration.

**Endpoint:** `GET /api/v1/info`

**Request:**
```bash
curl "http://localhost:8000/api/v1/info"
```

**Response:**
```json
{
  "environment": "development",
  "llm_provider": "ollama",
  "llm_model": "phi3.5:3.8b",
  "embedding_model": "mistral-embed",
  "rl_algorithm": "ppo",
  "max_retries": 3,
  "rag_top_k": 5,
  "chunk_size": 1000
}
```

---

## 📚 Interactive API Documentation

FastAPI provides automatic interactive API documentation:

### Swagger UI
```
http://localhost:8000/docs
```

### ReDoc
```
http://localhost:8000/redoc
```

---

## 🔄 Complete Workflow Example

Here's a complete workflow from upload to test results:

```bash
# 1. Upload API documentation
UPLOAD_RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@api_doc.json" \
  -F "name=My API" \
  -F "base_url=https://jsonplaceholder.typicode.com")

DOCUMENT_ID=$(echo $UPLOAD_RESPONSE | jq -r '.document_id')
echo "Document ID: $DOCUMENT_ID"

# 2. Start test execution
TEST_RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/tests/start" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOCUMENT_ID\", \"max_retries\": 3}")

SESSION_ID=$(echo $TEST_RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# 3. Poll for status (every 2 seconds)
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/tests/$SESSION_ID/status" | jq -r '.status')
  PROGRESS=$(curl -s "http://localhost:8000/api/v1/tests/$SESSION_ID/status" | jq -r '.progress')

  echo "Status: $STATUS, Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 2
done

# 4. Get final report
curl "http://localhost:8000/api/v1/tests/$SESSION_ID/report" | jq

# 5. Cleanup
curl -X DELETE "http://localhost:8000/api/v1/tests/$SESSION_ID"
curl -X DELETE "http://localhost:8000/api/v1/documents/$DOCUMENT_ID"
```

---

## 🐍 Python Example

```python
import httpx
import asyncio
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

async def test_api():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Upload document
        with open("api_doc.json", "rb") as f:
            files = {"file": ("api_doc.json", f, "application/json")}
            data = {"name": "My API", "base_url": "https://api.example.com"}

            upload_resp = await client.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data
            )
            document_id = upload_resp.json()["document_id"]
            print(f"Document ID: {document_id}")

        # 2. Start tests
        test_resp = await client.post(
            f"{BASE_URL}/tests/start",
            json={"document_id": document_id, "max_retries": 3}
        )
        session_id = test_resp.json()["session_id"]
        print(f"Session ID: {session_id}")

        # 3. Poll for completion
        while True:
            status_resp = await client.get(f"{BASE_URL}/tests/{session_id}/status")
            status_data = status_resp.json()

            print(f"Status: {status_data['status']}, Progress: {status_data['progress']:.1f}%")

            if status_data["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(2)

        # 4. Get report
        report_resp = await client.get(f"{BASE_URL}/tests/{session_id}/report")
        report = report_resp.json()

        print(f"\nTest Results:")
        print(f"  Total: {report['total_tests']}")
        print(f"  Passed: {report['passed']}")
        print(f"  Failed: {report['failed']}")
        print(f"  Success Rate: {report['success_rate']:.1f}%")

        # 5. Cleanup
        await client.delete(f"{BASE_URL}/tests/{session_id}")
        await client.delete(f"{BASE_URL}/documents/{document_id}")

asyncio.run(test_api())
```

---

## 📋 Error Responses

All errors follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "field": "additional_info"
  }
}
```

**Common HTTP Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## 🚀 Testing the API

Run the automated test script:

```bash
python test_api_endpoints.py
```

This will test all endpoints and verify the API is working correctly.
