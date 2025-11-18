"""
Benchmarks for Schema Validation
Tests performance of validating API responses against OpenAPI schemas
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.benchmark_runner import BenchmarkRunner
from src.validation.schema_validator import SchemaValidator


def create_sample_response():
    """Create a sample API response"""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@example.com",
        "name": "John Doe",
        "age": 30,
        "role": "user",
        "is_active": True,
        "created_at": "2025-01-18T10:30:00Z",
        "updated_at": "2025-01-18T14:20:00Z"
    }


def create_large_response():
    """Create a response with many fields"""
    response = {}
    for i in range(100):
        response[f"field_{i}"] = f"value_{i}" if i % 2 == 0 else i
    return response


def create_nested_response():
    """Create a response with nested objects"""
    return {
        "user": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "john@example.com",
            "profile": {
                "name": "John Doe",
                "age": 30,
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "country": "USA",
                    "postal_code": "10001"
                },
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True
                }
            }
        },
        "metadata": {
            "created_at": "2025-01-18T10:30:00Z",
            "updated_at": "2025-01-18T14:20:00Z",
            "version": 1
        }
    }


def create_simple_schema():
    """Create a simple validation schema"""
    return {
        "type": "object",
        "required": ["id", "email", "name"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "email": {"type": "string", "format": "email"},
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 18, "maximum": 120},
            "role": {"type": "string", "enum": ["admin", "user", "guest"]},
            "is_active": {"type": "boolean"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"}
        }
    }


def create_complex_schema():
    """Create a complex nested schema"""
    return {
        "type": "object",
        "required": ["user", "metadata"],
        "properties": {
            "user": {
                "type": "object",
                "required": ["id", "email", "profile"],
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "email": {"type": "string", "format": "email"},
                    "profile": {
                        "type": "object",
                        "required": ["name", "age", "address"],
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "address": {
                                "type": "object",
                                "properties": {
                                    "street": {"type": "string"},
                                    "city": {"type": "string"},
                                    "country": {"type": "string"},
                                    "postal_code": {"type": "string"}
                                }
                            },
                            "preferences": {
                                "type": "object",
                                "properties": {
                                    "theme": {"type": "string"},
                                    "language": {"type": "string"},
                                    "notifications": {"type": "boolean"}
                                }
                            }
                        }
                    }
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "version": {"type": "integer"}
                }
            }
        }
    }


def main():
    """Run schema validation benchmarks"""
    print("="*80)
    print("SCHEMA VALIDATION BENCHMARKS")
    print("="*80)

    runner = BenchmarkRunner(warmup_iterations=10)

    # Benchmark 1: Simple schema validation (permissive mode)
    validator_permissive = SchemaValidator(strict_mode=False)
    simple_response = create_sample_response()
    simple_schema = create_simple_schema()

    def bench_simple_permissive():
        validator_permissive.validate(simple_response, simple_schema)

    runner.benchmark(
        name="Schema Validation - Simple (Permissive Mode)",
        func=bench_simple_permissive,
        iterations=1000
    )

    # Benchmark 2: Simple schema validation (strict mode)
    validator_strict = SchemaValidator(strict_mode=True)

    def bench_simple_strict():
        validator_strict.validate(simple_response, simple_schema)

    runner.benchmark(
        name="Schema Validation - Simple (Strict Mode)",
        func=bench_simple_strict,
        iterations=1000
    )

    # Benchmark 3: Large flat object
    large_response = create_large_response()
    large_schema = {
        "type": "object",
        "properties": {f"field_{i}": {"type": "string" if i % 2 == 0 else "integer"} for i in range(100)}
    }

    def bench_large():
        validator_permissive.validate(large_response, large_schema)

    runner.benchmark(
        name="Schema Validation - Large Object (100 fields)",
        func=bench_large,
        iterations=500
    )

    # Benchmark 4: Deeply nested object
    nested_response = create_nested_response()
    complex_schema = create_complex_schema()

    def bench_nested():
        validator_permissive.validate(nested_response, complex_schema)

    runner.benchmark(
        name="Schema Validation - Deeply Nested Object",
        func=bench_nested,
        iterations=500
    )

    # Benchmark 5: Validation with violations
    invalid_response = {
        "id": "not-a-uuid",  # Invalid UUID
        "email": "not-an-email",  # Invalid email
        "name": "John",
        "age": 150,  # Out of range
        "role": "invalid-role"  # Invalid enum
    }

    def bench_with_violations():
        validator_permissive.validate(invalid_response, simple_schema)

    runner.benchmark(
        name="Schema Validation - With Violations (4 errors)",
        func=bench_with_violations,
        iterations=500
    )

    # Print summary
    runner.print_summary()

    # Save results
    runner.save_results("benchmarks/results/schema_validation.json")

    # Performance thresholds
    print("\n" + "="*80)
    print("PERFORMANCE THRESHOLDS")
    print("="*80)
    print("✅ GOOD: < 5ms per validation")
    print("⚠️  OK: 5-20ms per validation")
    print("❌ SLOW: > 20ms per validation")
    print("="*80)


if __name__ == "__main__":
    main()
