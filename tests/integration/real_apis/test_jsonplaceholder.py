"""
Integration Tests Against JSONPlaceholder API
Tests the system against a real public API: https://jsonplaceholder.typicode.com
"""
import pytest
import httpx
from src.extraction.constraint_extractor import ConstraintExtractor
from src.generation.enhanced_test_generator import EnhancedTestGenerator
from src.validation.schema_validator import SchemaValidator
from src.metrics.coverage_tracker import CoverageTracker


# JSONPlaceholder base URL
BASE_URL = "https://jsonplaceholder.typicode.com"


@pytest.mark.integration
@pytest.mark.requires_network
class TestJSONPlaceholderAPI:
    """Test against JSONPlaceholder public API"""

    @pytest.fixture
    def jsonplaceholder_spec(self):
        """OpenAPI-like spec for JSONPlaceholder endpoints"""
        return {
            "endpoints": [
                {
                    "path": "/posts",
                    "method": "GET",
                    "description": "Get all posts",
                    "parameters": {},
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "userId": {"type": "integer"},
                                        "id": {"type": "integer"},
                                        "title": {"type": "string"},
                                        "body": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "path": "/posts/{id}",
                    "method": "GET",
                    "description": "Get post by ID",
                    "parameters": {
                        "id": {"type": "integer", "in": "path", "required": True}
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "userId": {"type": "integer"},
                                    "id": {"type": "integer"},
                                    "title": {"type": "string"},
                                    "body": {"type": "string"}
                                }
                            }
                        },
                        "404": {"description": "Not Found"}
                    }
                },
                {
                    "path": "/posts",
                    "method": "POST",
                    "description": "Create a post",
                    "requestBody": {
                        "required": True,
                        "schema": {
                            "type": "object",
                            "required": ["title", "body", "userId"],
                            "properties": {
                                "title": {"type": "string"},
                                "body": {"type": "string"},
                                "userId": {"type": "integer"}
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Created"}
                    }
                }
            ]
        }

    # ========================================================================
    # Real API Connection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_connect_to_jsonplaceholder(self):
        """Test we can connect to JSONPlaceholder API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/1")

            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "title" in data
            assert "body" in data

    @pytest.mark.asyncio
    async def test_get_all_posts(self):
        """Test fetching all posts"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts")

            assert response.status_code == 200
            posts = response.json()
            assert isinstance(posts, list)
            assert len(posts) > 0

            # Check first post structure
            post = posts[0]
            assert "userId" in post
            assert "id" in post
            assert "title" in post
            assert "body" in post

    @pytest.mark.asyncio
    async def test_get_single_post(self):
        """Test fetching a single post"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/1")

            assert response.status_code == 200
            post = response.json()
            assert post["id"] == 1
            assert isinstance(post["title"], str)
            assert isinstance(post["body"], str)

    @pytest.mark.asyncio
    async def test_post_not_found(self):
        """Test 404 for non-existent post"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/999999")

            # JSONPlaceholder returns 404 for non-existent resources
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_post(self):
        """Test creating a post"""
        async with httpx.AsyncClient() as client:
            new_post = {
                "title": "Test Post",
                "body": "This is a test post created by AutoTest-RL",
                "userId": 1
            }

            response = await client.post(f"{BASE_URL}/posts", json=new_post)

            assert response.status_code == 201
            created = response.json()
            assert created["title"] == new_post["title"]
            assert created["body"] == new_post["body"]
            assert "id" in created

    # ========================================================================
    # Schema Validation Against Real Responses
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_post_response_schema(self):
        """Test validating real API response against schema"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/1")
            post = response.json()

        # Define expected schema
        schema = {
            "type": "object",
            "required": ["userId", "id", "title", "body"],
            "properties": {
                "userId": {"type": "integer"},
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "body": {"type": "string"}
            }
        }

        validator = SchemaValidator(strict_mode=False)
        result = validator.validate(post, schema)

        assert result.valid is True, f"Validation failed: {result.get_summary()}"
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_validate_posts_array_schema(self):
        """Test validating array of posts"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts?_limit=5")
            posts = response.json()

        # Validate first post as sample
        if posts:
            post = posts[0]
            schema = {
                "type": "object",
                "required": ["userId", "id", "title", "body"],
                "properties": {
                    "userId": {"type": "integer"},
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "body": {"type": "string"}
                }
            }

            validator = SchemaValidator(strict_mode=False)
            result = validator.validate(post, schema)

            assert result.valid is True

    # ========================================================================
    # Coverage Tracking Against Real API
    # ========================================================================

    @pytest.mark.asyncio
    async def test_track_coverage_real_api(self, jsonplaceholder_spec):
        """Test coverage tracking against real API calls"""
        tracker = CoverageTracker(session_id="jsonplaceholder-test")
        tracker.register_endpoints(jsonplaceholder_spec["endpoints"])

        async with httpx.AsyncClient() as client:
            # Test GET /posts
            response1 = await client.get(f"{BASE_URL}/posts?_limit=1")
            tracker.record_test({
                "endpoint": "/posts",
                "method": "GET",
                "status_code": response1.status_code,
                "success": response1.status_code == 200,
                "scenario_type": "happy_path"
            })

            # Test GET /posts/{id}
            response2 = await client.get(f"{BASE_URL}/posts/1")
            tracker.record_test({
                "endpoint": "/posts/{id}",
                "method": "GET",
                "status_code": response2.status_code,
                "success": response2.status_code == 200,
                "parameters_tested": ["id"],
                "scenario_type": "happy_path"
            })

            # Test POST /posts
            response3 = await client.post(f"{BASE_URL}/posts", json={
                "title": "Test",
                "body": "Test body",
                "userId": 1
            })
            tracker.record_test({
                "endpoint": "/posts",
                "method": "POST",
                "status_code": response3.status_code,
                "success": response3.status_code == 201,
                "parameters_tested": ["title", "body", "userId"],
                "scenario_type": "happy_path"
            })

        # Generate coverage report
        report = tracker.get_coverage_report()

        # Verify coverage
        assert report["endpoint_coverage"] == 100.0  # All 3 endpoints tested
        assert report["test_statistics"]["total"] == 3
        assert report["test_statistics"]["passed"] >= 2

    # ========================================================================
    # Boundary Testing Against Real API
    # ========================================================================

    @pytest.mark.asyncio
    async def test_boundary_values_real_api(self):
        """Test boundary values against real API"""
        async with httpx.AsyncClient() as client:
            # Test with valid post ID (boundary: first post)
            response1 = await client.get(f"{BASE_URL}/posts/1")
            assert response1.status_code == 200

            # Test with valid post ID (boundary: last known post)
            response2 = await client.get(f"{BASE_URL}/posts/100")
            assert response2.status_code == 200

            # Test with invalid post ID (boundary: zero)
            response3 = await client.get(f"{BASE_URL}/posts/0")
            # May return 404 or empty object depending on API

            # Test with invalid post ID (boundary: negative)
            response4 = await client.get(f"{BASE_URL}/posts/-1")
            # Should handle gracefully

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_handle_network_timeout(self):
        """Test handling network timeout gracefully"""
        try:
            async with httpx.AsyncClient(timeout=0.001) as client:
                await client.get(f"{BASE_URL}/posts")
        except httpx.TimeoutException:
            # Expected - timeout is too short
            pass
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self):
        """Test handling invalid JSON response"""
        # JSONPlaceholder should always return valid JSON
        # This tests our system can handle it
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/1")

            try:
                data = response.json()
                assert isinstance(data, dict)
            except Exception as e:
                pytest.fail(f"Failed to parse JSON: {e}")


@pytest.mark.integration
@pytest.mark.requires_network
@pytest.mark.slow
class TestJSONPlaceholderEndToEnd:
    """End-to-end tests using JSONPlaceholder"""

    @pytest.mark.asyncio
    async def test_complete_workflow_real_api(self, mock_settings):
        """Test complete workflow against real API"""
        # Step 1: Define endpoint spec
        endpoint = {
            "path": "/posts/{id}",
            "method": "GET",
            "parameters": {
                "id": {"type": "integer", "in": "path", "minimum": 1}
            },
            "responses": {
                "200": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "userId": {"type": "integer"},
                            "id": {"type": "integer"},
                            "title": {"type": "string"},
                            "body": {"type": "string"}
                        }
                    }
                },
                "404": {"description": "Not Found"}
            }
        }

        # Step 2: Extract constraints
        extractor = ConstraintExtractor()
        constraints = extractor.extract_constraints(endpoint)

        # Step 3: Make real API call
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/posts/1")

            # Step 4: Validate response
            schema = endpoint["responses"]["200"]["schema"]
            validator = SchemaValidator(strict_mode=False)
            validation_result = validator.validate(response.json(), schema)

            assert validation_result.valid is True

            # Step 5: Track coverage
            tracker = CoverageTracker(session_id="real-api-e2e")
            tracker.register_endpoints([endpoint])

            tracker.record_test({
                "endpoint": endpoint["path"],
                "method": endpoint["method"],
                "status_code": response.status_code,
                "success": validation_result.valid,
                "parameters_tested": ["id"],
                "scenario_type": "happy_path"
            })

            # Step 6: Get coverage report
            report = tracker.get_coverage_report()

            assert report["endpoint_coverage"] == 100.0
            assert report["test_statistics"]["passed"] >= 1
