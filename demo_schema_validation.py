"""
Demo: Schema Validation
Demonstrates validating API responses against OpenAPI schemas
"""
from src.validation.schema_validator import SchemaValidator, ViolationType, Severity
from src.validation.openapi_schema_parser import OpenAPISchemaParser

# Simple logger
class SimpleLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def warning(self, msg, **kwargs): print(f"WARN: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    def debug(self, msg, **kwargs): pass

logger = SimpleLogger()


def create_sample_openapi_spec():
    """Create a sample OpenAPI specification"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "User API",
            "version": "1.0.0"
        },
        "paths": {
            "/api/users": {
                "get": {
                    "summary": "List users",
                    "responses": {
                        "200": {
                            "description": "List of users",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/UserCreate"
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "User created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/users/{id}": {
                "get": {
                    "summary": "Get user by ID",
                    "responses": {
                        "200": {
                            "description": "User details",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "User not found",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "email", "name"],
                    "properties": {
                        "id": {
                            "type": "integer",
                            "minimum": 1
                        },
                        "email": {
                            "type": "string",
                            "format": "email"
                        },
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 100
                        },
                        "age": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 150
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "inactive", "pending"]
                        }
                    }
                },
                "UserCreate": {
                    "type": "object",
                    "required": ["email", "name"],
                    "properties": {
                        "email": {
                            "type": "string",
                            "format": "email"
                        },
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 100
                        },
                        "age": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 150
                        }
                    }
                },
                "Error": {
                    "type": "object",
                    "required": ["error", "message"],
                    "properties": {
                        "error": {
                            "type": "string"
                        },
                        "message": {
                            "type": "string"
                        },
                        "details": {
                            "type": "object"
                        }
                    }
                }
            }
        }
    }


def demo_schema_parsing():
    """Demo: Parse OpenAPI spec and extract schemas"""
    logger.info("=" * 80)
    logger.info("DEMO 1: OpenAPI Schema Parsing")
    logger.info("=" * 80)
    logger.info("")

    spec = create_sample_openapi_spec()

    logger.info("📖 Parsing OpenAPI specification...")
    parser = OpenAPISchemaParser(spec)

    logger.info(f"   Version: {parser.version}")
    logger.info("")

    # Extract all endpoint schemas
    endpoint_schemas = parser.extract_endpoint_schemas()

    logger.info(f"📊 Extracted {len(endpoint_schemas)} endpoint schemas:")
    logger.info("")

    for endpoint_key, schema in endpoint_schemas.items():
        logger.info(f"Endpoint: {endpoint_key}")
        logger.info(f"   Path: {schema.path}")
        logger.info(f"   Method: {schema.method}")

        if schema.request_schema:
            logger.info(f"   Request schema: {list(schema.request_schema.get('properties', {}).keys())}")

        logger.info(f"   Response schemas: {list(schema.response_schemas.keys())}")
        logger.info("")

    return parser


def demo_valid_response():
    """Demo: Validate a valid response"""
    logger.info("=" * 80)
    logger.info("DEMO 2: Validate Valid Response")
    logger.info("=" * 80)
    logger.info("")

    # Valid user object
    valid_user = {
        "id": 123,
        "email": "john@example.com",
        "name": "John Doe",
        "age": 30,
        "status": "active"
    }

    # Schema
    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer", "minimum": 1},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
        }
    }

    logger.info("User data:")
    logger.info(f"   {valid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(valid_user, schema)

    logger.info(result.get_summary())
    logger.info("")


def demo_missing_required_field():
    """Demo: Detect missing required field"""
    logger.info("=" * 80)
    logger.info("DEMO 3: Missing Required Field")
    logger.info("=" * 80)
    logger.info("")

    # User missing required 'name' field
    invalid_user = {
        "id": 123,
        "email": "john@example.com",
        # "name" is missing!
        "age": 30
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"}
        }
    }

    logger.info("User data (missing 'name'):")
    logger.info(f"   {invalid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(invalid_user, schema)

    logger.info(result.get_summary())
    logger.info("")

    for violation in result.violations:
        logger.error(f"Violation: {violation.violation_type.value}")
        logger.error(f"   Severity: {violation.severity.value}")
        logger.error(f"   Field: {violation.field_path}")
        logger.error(f"   Description: {violation.description}")
        logger.info("")


def demo_wrong_type():
    """Demo: Detect wrong field type"""
    logger.info("=" * 80)
    logger.info("DEMO 4: Wrong Field Type")
    logger.info("=" * 80)
    logger.info("")

    # User with wrong type for 'id' (string instead of integer)
    invalid_user = {
        "id": "not-a-number",  # Should be integer!
        "email": "john@example.com",
        "name": "John Doe"
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"}
        }
    }

    logger.info("User data (id is string, not integer):")
    logger.info(f"   {invalid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(invalid_user, schema)

    logger.info(result.get_summary())
    logger.info("")

    for violation in result.violations:
        logger.error(f"Violation: {violation.violation_type.value}")
        logger.error(f"   Expected: {violation.expected}")
        logger.error(f"   Actual: {violation.actual}")
        logger.error(f"   Description: {violation.description}")
        logger.info("")


def demo_invalid_format():
    """Demo: Detect invalid format (email)"""
    logger.info("=" * 80)
    logger.info("DEMO 5: Invalid Format")
    logger.info("=" * 80)
    logger.info("")

    # User with invalid email format
    invalid_user = {
        "id": 123,
        "email": "not-an-email",  # Invalid email format!
        "name": "John Doe"
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"}
        }
    }

    logger.info("User data (invalid email format):")
    logger.info(f"   {invalid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(invalid_user, schema)

    logger.info(result.get_summary())
    logger.info("")

    for violation in result.violations:
        logger.error(f"Violation: {violation.violation_type.value}")
        logger.error(f"   Expected: {violation.expected}")
        logger.error(f"   Actual: {violation.actual}")
        logger.error(f"   Description: {violation.description}")
        logger.info("")


def demo_out_of_range():
    """Demo: Detect out of range value"""
    logger.info("=" * 80)
    logger.info("DEMO 6: Out of Range Value")
    logger.info("=" * 80)
    logger.info("")

    # User with age out of valid range
    invalid_user = {
        "id": 123,
        "email": "john@example.com",
        "name": "John Doe",
        "age": 200  # Exceeds maximum of 150!
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150}
        }
    }

    logger.info("User data (age out of range):")
    logger.info(f"   {invalid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(invalid_user, schema)

    logger.info(result.get_summary())
    logger.info("")

    for violation in result.violations:
        logger.error(f"Violation: {violation.violation_type.value}")
        logger.error(f"   Expected: {violation.expected}")
        logger.error(f"   Actual: {violation.actual}")
        logger.error(f"   Description: {violation.description}")
        logger.info("")


def demo_invalid_enum():
    """Demo: Detect invalid enum value"""
    logger.info("=" * 80)
    logger.info("DEMO 7: Invalid Enum Value")
    logger.info("=" * 80)
    logger.info("")

    # User with invalid status enum
    invalid_user = {
        "id": 123,
        "email": "john@example.com",
        "name": "John Doe",
        "status": "deleted"  # Not in enum! Valid: active, inactive, pending
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
        }
    }

    logger.info("User data (invalid enum value):")
    logger.info(f"   {invalid_user}")
    logger.info("")

    validator = SchemaValidator(strict_mode=False)
    result = validator.validate(invalid_user, schema)

    logger.info(result.get_summary())
    logger.info("")

    for violation in result.violations:
        logger.error(f"Violation: {violation.violation_type.value}")
        logger.error(f"   Expected: {violation.expected}")
        logger.error(f"   Actual: {violation.actual}")
        logger.error(f"   Description: {violation.description}")
        logger.info("")


def demo_strict_mode():
    """Demo: Strict mode rejects unexpected fields"""
    logger.info("=" * 80)
    logger.info("DEMO 8: Strict Mode - Unexpected Fields")
    logger.info("=" * 80)
    logger.info("")

    # User with extra field not in schema
    user_with_extra = {
        "id": 123,
        "email": "john@example.com",
        "name": "John Doe",
        "extra_field": "unexpected"  # Not in schema!
    }

    schema = {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string"},
            "name": {"type": "string"}
        }
    }

    logger.info("User data (has extra field 'extra_field'):")
    logger.info(f"   {user_with_extra}")
    logger.info("")

    # Test with strict_mode=False (permissive)
    logger.info("Testing with strict_mode=False:")
    validator_permissive = SchemaValidator(strict_mode=False)
    result_permissive = validator_permissive.validate(user_with_extra, schema)
    logger.info(f"   {result_permissive.get_summary()}")
    logger.info("")

    # Test with strict_mode=True (strict)
    logger.info("Testing with strict_mode=True:")
    validator_strict = SchemaValidator(strict_mode=True)
    result_strict = validator_strict.validate(user_with_extra, schema)
    logger.info(f"   {result_strict.get_summary()}")

    if result_strict.violations:
        for violation in result_strict.violations:
            logger.warning(f"   Warning: {violation.description}")

    logger.info("")


def main():
    """Run all schema validation demos"""
    logger.info("=" * 80)
    logger.info("SCHEMA VALIDATION DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Demo 1: Parse OpenAPI spec
    parser = demo_schema_parsing()

    # Demo 2: Valid response
    demo_valid_response()

    # Demo 3: Missing required field
    demo_missing_required_field()

    # Demo 4: Wrong type
    demo_wrong_type()

    # Demo 5: Invalid format
    demo_invalid_format()

    # Demo 6: Out of range
    demo_out_of_range()

    # Demo 7: Invalid enum
    demo_invalid_enum()

    # Demo 8: Strict mode
    demo_strict_mode()

    # Summary
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")

    logger.info("✅ Schema validation features demonstrated:")
    logger.info("   1. OpenAPI spec parsing and schema extraction")
    logger.info("   2. Valid response validation")
    logger.info("   3. Missing required field detection")
    logger.info("   4. Wrong type detection")
    logger.info("   5. Invalid format detection (email, URI, UUID, etc.)")
    logger.info("   6. Out of range value detection (min/max)")
    logger.info("   7. Invalid enum value detection")
    logger.info("   8. Strict mode for unexpected fields")
    logger.info("")

    logger.info("🎯 Integration with TestRunner:")
    logger.info("   runner = TestRunner(...)")
    logger.info("   results = await runner.validate_schemas(")
    logger.info("       endpoints=endpoints,")
    logger.info("       openapi_spec=spec,")
    logger.info("       base_url='http://localhost:8000',")
    logger.info("       strict_mode=True")
    logger.info("   )")
    logger.info("")

    logger.info("📊 Benefits:")
    logger.info("   ✓ Catch schema violations before production")
    logger.info("   ✓ Ensure API responses match documentation")
    logger.info("   ✓ Detect breaking changes automatically")
    logger.info("   ✓ Validate field types, formats, ranges")
    logger.info("   ✓ Enforce required fields")
    logger.info("   ✓ Support for $ref and nested schemas")
    logger.info("")


if __name__ == "__main__":
    main()
