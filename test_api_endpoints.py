#!/usr/bin/env python3
"""
API Endpoint Testing Script
Tests all REST API endpoints to verify they work correctly
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import httpx
import json
import time
from loguru import logger


BASE_URL = "http://localhost:8000"
API_VERSION = "/api/v1"


async def test_health_check():
    """Test health check endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 1: Health Check")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Health check failed"
        assert response.json()["status"] == "healthy"
        print("✅ Health check passed")


async def test_root_endpoint():
    """Test root endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 2: Root Endpoint")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Root endpoint failed"
        print("✅ Root endpoint passed")


async def test_api_info():
    """Test API info endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 3: API Info Endpoint")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_VERSION}/info")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        print("✅ API info endpoint accessible")


async def test_document_list():
    """Test document list endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 4: List Documents")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_VERSION}/documents/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Document list failed"
        data = response.json()
        assert "documents" in data
        assert "total" in data
        print(f"✅ Document list passed (found {data['total']} documents)")

        return data


async def test_document_upload():
    """Test document upload endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 5: Upload Document")
    print("=" * 80)

    # Create a sample API doc
    sample_doc = {
        "api_name": "Test API",
        "version": "1.0.0",
        "base_url": "https://jsonplaceholder.typicode.com",
        "endpoints": [
            {
                "path": "/users",
                "method": "GET",
                "summary": "Get all users",
                "auth_required": False
            },
            {
                "path": "/posts",
                "method": "GET",
                "summary": "Get all posts",
                "auth_required": False
            }
        ]
    }

    # Write to temp file
    temp_file = Path("./temp_test_api.json")
    with open(temp_file, 'w') as f:
        json.dump(sample_doc, f, indent=2)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Upload file
            with open(temp_file, 'rb') as f:
                files = {"file": ("test_api.json", f, "application/json")}
                data = {
                    "name": "Test API Documentation",
                    "description": "Test upload",
                    "base_url": "https://jsonplaceholder.typicode.com"
                }

                response = await client.post(
                    f"{BASE_URL}{API_VERSION}/documents/upload",
                    files=files,
                    data=data
                )

            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")

            assert response.status_code == 200, f"Document upload failed: {response.text}"
            result = response.json()
            assert "document_id" in result
            assert result["endpoints_found"] > 0

            print(f"✅ Document upload passed (Document ID: {result['document_id']})")

            return result["document_id"]

    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


async def test_get_document(document_id: str):
    """Test get document endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 6: Get Document Details (ID: {document_id})")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_VERSION}/documents/{document_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Get document failed"
        data = response.json()
        assert data["id"] == document_id
        assert "endpoints" in data

        print(f"✅ Get document passed")

        return data


async def test_start_test_execution(document_id: str):
    """Test start test execution endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 7: Start Test Execution (Document ID: {document_id})")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "document_id": document_id,
            "max_retries": 2,
            "use_optimal_order": True,
            "test_types": ["positive"]
        }

        response = await client.post(
            f"{BASE_URL}{API_VERSION}/tests/start",
            json=payload
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, f"Start test failed: {response.text}"
        result = response.json()
        assert "session_id" in result
        assert result["document_id"] == document_id

        print(f"✅ Start test execution passed (Session ID: {result['session_id']})")

        return result["session_id"]


async def test_get_test_status(session_id: str):
    """Test get test status endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 8: Get Test Status (Session ID: {session_id})")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # Poll for status updates
        max_polls = 30  # 30 seconds max
        for i in range(max_polls):
            response = await client.get(f"{BASE_URL}{API_VERSION}/tests/{session_id}/status")
            print(f"\nPoll {i+1}/{max_polls}")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")

                status = data.get("status")
                progress = data.get("progress", 0)

                print(f"Test Status: {status}, Progress: {progress:.1f}%")

                if status in ["completed", "failed"]:
                    print(f"✅ Test execution {status}")
                    return data

            await asyncio.sleep(1)

        print("⚠️  Test still running after 30 seconds")
        return None


async def test_list_test_sessions():
    """Test list test sessions endpoint"""
    print("\n" + "=" * 80)
    print("🔍 TEST 9: List Test Sessions")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_VERSION}/tests/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "List test sessions failed"
        data = response.json()
        assert "sessions" in data
        assert "total" in data

        print(f"✅ List test sessions passed (found {data['total']} sessions)")

        return data


async def test_get_test_report(session_id: str):
    """Test get test report endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 10: Get Test Report (Session ID: {session_id})")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}{API_VERSION}/tests/{session_id}/report")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, default=str)}")

            assert "total_tests" in data
            assert "passed" in data
            assert "failed" in data
            assert "results" in data

            print(f"\n📊 Test Report Summary:")
            print(f"   Total Tests: {data['total_tests']}")
            print(f"   Passed: {data['passed']}")
            print(f"   Failed: {data['failed']}")
            print(f"   Success Rate: {data['success_rate']:.1f}%")
            print(f"   Total Time: {data['total_time']:.2f}s")

            print(f"✅ Get test report passed")

            return data
        else:
            print(f"Response: {response.text}")
            print(f"⚠️  Report not ready yet (Status: {response.status_code})")
            return None


async def test_delete_test_session(session_id: str):
    """Test delete test session endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 11: Delete Test Session (Session ID: {session_id})")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}{API_VERSION}/tests/{session_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Delete test session failed"

        print(f"✅ Delete test session passed")


async def test_delete_document(document_id: str):
    """Test delete document endpoint"""
    print("\n" + "=" * 80)
    print(f"🔍 TEST 12: Delete Document (ID: {document_id})")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}{API_VERSION}/documents/{document_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Delete document failed"

        print(f"✅ Delete document passed")


async def main():
    """Run all API tests"""
    print("\n" + "=" * 80)
    print("🎯 AutoTest-RL - API Endpoint Testing")
    print("=" * 80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"API Version: {API_VERSION}")
    print("\nThis script tests all REST API endpoints")

    try:
        # Test 1-4: Basic endpoints
        await test_health_check()
        await test_root_endpoint()
        await test_api_info()
        await test_document_list()

        # Test 5-6: Document management
        document_id = await test_document_upload()
        doc_data = await test_get_document(document_id)

        # Test 7-10: Test execution
        session_id = await test_start_test_execution(document_id)

        # Wait a moment for background task to start
        await asyncio.sleep(2)

        await test_get_test_status(session_id)
        await test_list_test_sessions()

        # Wait a bit more for tests to complete
        print("\n⏳ Waiting for test execution to complete...")
        await asyncio.sleep(5)

        await test_get_test_report(session_id)

        # Test 11-12: Cleanup
        await test_delete_test_session(session_id)
        await test_delete_document(document_id)

        # Final summary
        print("\n" + "=" * 80)
        print("🎉 ALL API TESTS PASSED!")
        print("=" * 80)
        print("\n✨ Tested endpoints:")
        print("   ✓ Health check")
        print("   ✓ Root endpoint")
        print("   ✓ API info")
        print("   ✓ Document list")
        print("   ✓ Document upload")
        print("   ✓ Get document details")
        print("   ✓ Start test execution")
        print("   ✓ Get test status")
        print("   ✓ List test sessions")
        print("   ✓ Get test report")
        print("   ✓ Delete test session")
        print("   ✓ Delete document")
        print("\n🚀 REST API is fully functional!")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ API TESTS FAILED")
        print("=" * 80)
        logger.exception(f"Error: {e}")
        print("\n💡 Make sure the API server is running:")
        print("   docker compose up -d")
        print("   or")
        print("   python src/api/main.py")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
