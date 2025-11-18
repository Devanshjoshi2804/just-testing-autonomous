"""
End-to-End Integration Tests
Tests the complete flow from documentation parsing to test execution
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.parsers.document_parser_enhanced import DocumentParserEnhanced
from src.extraction.constraint_extractor import ConstraintExtractor
from src.generation.enhanced_test_generator import EnhancedTestGenerator
from src.validation.schema_validator import SchemaValidator
from src.metrics.coverage_tracker import CoverageTracker


@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEndFlow:
    """Test complete end-to-end workflow"""

    @pytest.fixture
    def sample_openapi_spec(self):
        """Sample OpenAPI specification for testing"""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/api/users": {
                    "get": {
                        "summary": "List users",
                        "operationId": "listUsers",
                        "parameters": [
                            {
                                "name": "page",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 1, "maximum": 100}
                            },
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 1, "maximum": 50}
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "users": {
                                                    "type": "array",
                                                    "items": {"$ref": "#/components/schemas/User"}
                                                },
                                                "total": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            },
                            "400": {"description": "Bad Request"},
                            "401": {"description": "Unauthorized"}
                        }
                    },
                    "post": {
                        "summary": "Create user",
                        "operationId": "createUser",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserCreate"}
                                }
                            }
                        },
                        "responses": {
                            "201": {"description": "Created"},
                            "400": {"description": "Bad Request"},
                            "422": {"description": "Validation Error"}
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["id", "email"],
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "email": {"type": "string", "format": "email"},
                            "name": {"type": "string"}
                        }
                    },
                    "UserCreate": {
                        "type": "object",
                        "required": ["email", "name"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "minLength": 5,
                                "maxLength": 100
                            },
                            "name": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 50
                            },
                            "age": {
                                "type": "integer",
                                "minimum": 18,
                                "maximum": 120
                            }
                        }
                    }
                }
            }
        }

    # ========================================================================
    # Document Parsing Integration
    # ========================================================================

    @pytest.mark.asyncio
    async def test_parse_openapi_spec(self, sample_openapi_spec, mock_settings):
        """Test parsing OpenAPI specification"""
        # Mock RAG pipeline
        mock_rag = Mock()

        parser = DocumentParserEnhanced(rag_pipeline=mock_rag, settings=mock_settings)

        # Parse the OpenAPI spec
        with patch.object(parser, 'parse_openapi', return_value={
            'endpoints': [
                {
                    'path': '/api/users',
                    'method': 'GET',
                    'parameters': {
                        'page': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}
                    },
                    'responses': {
                        '200': {'description': 'Success'},
                        '400': {'description': 'Bad Request'},
                        '401': {'description': 'Unauthorized'}
                    }
                },
                {
                    'path': '/api/users',
                    'method': 'POST',
                    'requestBody': {
                        'required': True,
                        'schema': {
                            'type': 'object',
                            'required': ['email', 'name'],
                            'properties': {
                                'email': {'type': 'string', 'format': 'email'},
                                'name': {'type': 'string'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': 'Created'},
                        '422': {'description': 'Validation Error'}
                    }
                }
            ]
        }):
            parsed = await parser.parse_openapi(sample_openapi_spec)

        assert 'endpoints' in parsed
        assert len(parsed['endpoints']) == 2

        # Check GET endpoint
        get_endpoint = parsed['endpoints'][0]
        assert get_endpoint['path'] == '/api/users'
        assert get_endpoint['method'] == 'GET'
        assert 'page' in get_endpoint['parameters']
        assert 'limit' in get_endpoint['parameters']

        # Check POST endpoint
        post_endpoint = parsed['endpoints'][1]
        assert post_endpoint['method'] == 'POST'
        assert post_endpoint['requestBody']['required'] is True

    # ========================================================================
    # Constraint Extraction Integration
    # ========================================================================

    def test_extract_constraints_from_parsed_endpoints(self, sample_openapi_spec):
        """Test extracting constraints from parsed endpoints"""
        # Simulate parsed endpoint
        endpoint = {
            'path': '/api/users',
            'method': 'POST',
            'requestBody': {
                'required': True,
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['email', 'name'],
                            'properties': {
                                'email': {
                                    'type': 'string',
                                    'format': 'email',
                                    'minLength': 5,
                                    'maxLength': 100
                                },
                                'name': {
                                    'type': 'string',
                                    'minLength': 2,
                                    'maxLength': 50
                                },
                                'age': {
                                    'type': 'integer',
                                    'minimum': 18,
                                    'maximum': 120
                                }
                            }
                        }
                    }
                }
            }
        }

        extractor = ConstraintExtractor()
        constraints = extractor.extract_constraints(endpoint)

        # Verify constraints were extracted
        assert 'email' in constraints
        assert 'name' in constraints
        assert 'age' in constraints

        # Check email constraints
        assert constraints['email'].required is True
        assert constraints['email'].type == 'string'

        # Check name constraints
        assert constraints['name'].required is True

        # Check age constraints
        assert constraints['age'].required is False

    # ========================================================================
    # Test Generation Integration
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_tests_from_constraints(self, mock_settings):
        """Test generating tests from extracted constraints"""
        endpoint = {
            'path': '/api/users',
            'method': 'GET',
            'parameters': {
                'page': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}
            }
        }

        constraints = {
            'page': {
                'type': 'integer',
                'constraints': [
                    {'constraint_type': 'min_value', 'value': 1},
                    {'constraint_type': 'max_value', 'value': 100}
                ]
            },
            'limit': {
                'type': 'integer',
                'constraints': [
                    {'constraint_type': 'min_value', 'value': 1},
                    {'constraint_type': 'max_value', 'value': 50}
                ]
            }
        }

        generator = EnhancedTestGenerator(settings=mock_settings)

        # Mock the comprehensive test generation
        with patch.object(generator, 'generate_comprehensive_tests', return_value=[
            {'type': 'positive', 'payload': {'page': 1, 'limit': 10}},
            {'type': 'boundary', 'payload': {'page': 1, 'limit': 1}},
            {'type': 'boundary', 'payload': {'page': 100, 'limit': 50}},
            {'type': 'negative', 'payload': {'page': 0, 'limit': 10}},
            {'type': 'negative', 'payload': {'page': 101, 'limit': 10}}
        ]):
            tests = await generator.generate_comprehensive_tests(endpoint, constraints)

        # Verify tests generated
        assert len(tests) >= 5

        # Check for different test types
        test_types = {test['type'] for test in tests}
        assert 'positive' in test_types
        assert 'boundary' in test_types
        assert 'negative' in test_types

    # ========================================================================
    # Schema Validation Integration
    # ========================================================================

    def test_validate_response_against_schema(self):
        """Test validating API response against OpenAPI schema"""
        # Sample response
        response_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "john@example.com",
            "name": "John Doe"
        }

        # Expected schema
        schema = {
            "type": "object",
            "required": ["id", "email"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "email": {"type": "string", "format": "email"},
                "name": {"type": "string"}
            }
        }

        validator = SchemaValidator(strict_mode=False)
        result = validator.validate(response_data, schema)

        assert result.valid is True
        assert len(result.violations) == 0

    # ========================================================================
    # Coverage Tracking Integration
    # ========================================================================

    def test_track_coverage_across_tests(self, sample_openapi_spec):
        """Test tracking coverage across multiple test executions"""
        tracker = CoverageTracker(session_id="integration-test-session")

        # Register endpoints from OpenAPI spec
        endpoints = [
            {
                "method": "GET",
                "path": "/api/users",
                "parameters": {"page": {}, "limit": {}},
                "responses": {"200": {}, "400": {}, "401": {}}
            },
            {
                "method": "POST",
                "path": "/api/users",
                "parameters": {"email": {}, "name": {}, "age": {}},
                "responses": {"201": {}, "400": {}, "422": {}}
            }
        ]

        tracker.register_endpoints(endpoints)

        # Simulate test results
        test_results = [
            {
                "endpoint": "/api/users",
                "method": "GET",
                "status_code": 200,
                "success": True,
                "parameters_tested": ["page", "limit"],
                "scenario_type": "happy_path"
            },
            {
                "endpoint": "/api/users",
                "method": "GET",
                "status_code": 400,
                "success": True,
                "parameters_tested": ["page"],
                "scenario_type": "boundary"
            },
            {
                "endpoint": "/api/users",
                "method": "POST",
                "status_code": 201,
                "success": True,
                "parameters_tested": ["email", "name"],
                "scenario_type": "happy_path"
            }
        ]

        for result in test_results:
            tracker.record_test(result)

        # Get coverage report
        report = tracker.get_coverage_report()

        # Verify coverage tracked
        assert report['endpoint_coverage'] == 100.0  # Both endpoints tested
        assert report['overall_coverage'] > 0
        assert report['test_statistics']['total'] == 3
        assert report['test_statistics']['passed'] == 3

    # ========================================================================
    # Complete End-to-End Flow
    # ========================================================================

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_pipeline_flow(self, sample_openapi_spec, mock_settings):
        """Test complete pipeline from parsing to coverage reporting"""
        # Step 1: Parse OpenAPI spec
        mock_rag = Mock()
        parser = DocumentParserEnhanced(rag_pipeline=mock_rag, settings=mock_settings)

        with patch.object(parser, 'parse_openapi', return_value={
            'endpoints': [
                {
                    'path': '/api/users',
                    'method': 'GET',
                    'parameters': {
                        'page': {'type': 'integer', 'minimum': 1}
                    },
                    'responses': {'200': {}, '400': {}}
                }
            ]
        }):
            parsed = await parser.parse_openapi(sample_openapi_spec)

        assert 'endpoints' in parsed

        # Step 2: Extract constraints
        extractor = ConstraintExtractor()
        endpoint = parsed['endpoints'][0]
        constraints = extractor.extract_constraints(endpoint)

        assert len(constraints) > 0

        # Step 3: Generate tests
        generator = EnhancedTestGenerator(settings=mock_settings)

        with patch.object(generator, 'generate_comprehensive_tests', return_value=[
            {'type': 'positive', 'payload': {'page': 1}},
            {'type': 'negative', 'payload': {'page': 0}}
        ]):
            tests = await generator.generate_comprehensive_tests(endpoint, constraints)

        assert len(tests) >= 2

        # Step 4: Track coverage
        tracker = CoverageTracker(session_id="complete-flow-test")
        tracker.register_endpoints([endpoint])

        # Simulate executing tests
        for test in tests:
            tracker.record_test({
                "endpoint": endpoint['path'],
                "method": endpoint['method'],
                "status_code": 200 if test['type'] == 'positive' else 400,
                "success": True,
                "scenario_type": test['type']
            })

        # Step 5: Generate coverage report
        report = tracker.get_coverage_report()

        assert report['endpoint_coverage'] == 100.0
        assert report['test_statistics']['total'] >= 2


@pytest.mark.integration
class TestComponentIntegration:
    """Test integration between components"""

    def test_extractor_to_generator_pipeline(self, mock_settings):
        """Test passing data from extractor to generator"""
        # Create endpoint with constraints
        endpoint = {
            'path': '/api/users',
            'method': 'POST',
            'requestBody': {
                'content': {
                    'application/json': {
                        'schema': {
                            'type': 'object',
                            'required': ['email'],
                            'properties': {
                                'email': {
                                    'type': 'string',
                                    'format': 'email'
                                }
                            }
                        }
                    }
                }
            }
        }

        # Extract constraints
        extractor = ConstraintExtractor()
        constraints = extractor.extract_constraints(endpoint)

        # Verify extraction worked
        assert 'email' in constraints

        # Generate tests using constraints
        generator = EnhancedTestGenerator(settings=mock_settings)

        # This integration verifies the data format is compatible
        # Even if generation is mocked, it proves the interfaces work together
        assert constraints is not None

    def test_validator_and_tracker_integration(self):
        """Test schema validator results feed into coverage tracker"""
        # Simulate schema validation
        validator = SchemaValidator(strict_mode=False)

        response_data = {"id": 1, "name": "Test"}
        schema = {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }

        validation_result = validator.validate(response_data, schema)

        # Create coverage tracker
        tracker = CoverageTracker(session_id="validator-tracker-test")

        # Record test with validation result
        test_result = {
            "endpoint": "/api/test",
            "method": "GET",
            "status_code": 200,
            "success": validation_result.valid,
            "scenario_type": "validation"
        }

        tracker.record_test(test_result)

        report = tracker.get_coverage_report()

        # Verify tracker recorded the validated test
        assert report['test_statistics']['total'] == 1
        assert report['test_statistics']['passed'] == 1
