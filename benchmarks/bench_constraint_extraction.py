"""
Benchmarks for Constraint Extraction
Tests performance of extracting constraints from API documentation
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.benchmark_runner import BenchmarkRunner
from src.analysis.constraint_extractor import ConstraintExtractor


def create_sample_endpoint():
    """Create a sample endpoint with various constraints"""
    return {
        "path": "/api/users",
        "method": "POST",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "name", "age"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "format": "email",
                                "minLength": 5,
                                "maxLength": 100,
                                "description": "User's email address"
                            },
                            "name": {
                                "type": "string",
                                "minLength": 2,
                                "maxLength": 50,
                                "pattern": "^[a-zA-Z ]+$",
                                "description": "User's full name"
                            },
                            "age": {
                                "type": "integer",
                                "minimum": 18,
                                "maximum": 120,
                                "description": "User's age (must be 18+)"
                            },
                            "username": {
                                "type": "string",
                                "minLength": 3,
                                "maxLength": 20,
                                "pattern": "^[a-zA-Z0-9_]+$",
                                "description": "Unique username"
                            },
                            "bio": {
                                "type": "string",
                                "maxLength": 500,
                                "description": "User biography (optional)"
                            },
                            "role": {
                                "type": "string",
                                "enum": ["admin", "user", "guest"],
                                "description": "User role in the system"
                            }
                        }
                    }
                }
            }
        },
        "responses": {
            "201": {"description": "Created"},
            "400": {"description": "Bad Request"},
            "422": {"description": "Validation Error"}
        }
    }


def create_large_endpoint():
    """Create an endpoint with many parameters"""
    properties = {}
    for i in range(50):
        properties[f"field_{i}"] = {
            "type": "string" if i % 2 == 0 else "integer",
            "minLength": 1 if i % 2 == 0 else None,
            "maxLength": 100 if i % 2 == 0 else None,
            "minimum": 0 if i % 2 == 1 else None,
            "maximum": 1000 if i % 2 == 1 else None
        }
        # Remove None values
        properties[f"field_{i}"] = {k: v for k, v in properties[f"field_{i}"].items() if v is not None}

    return {
        "path": "/api/complex",
        "method": "POST",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": properties
                    }
                }
            }
        }
    }


def main():
    """Run constraint extraction benchmarks"""
    print("="*80)
    print("CONSTRAINT EXTRACTION BENCHMARKS")
    print("="*80)

    runner = BenchmarkRunner(warmup_iterations=10)
    extractor = ConstraintExtractor()

    # Benchmark 1: Simple endpoint (6 fields)
    simple_endpoint = create_sample_endpoint()

    def bench_simple():
        extractor.extract_constraints(simple_endpoint)

    runner.benchmark(
        name="Extract Constraints - Simple Endpoint (6 fields)",
        func=bench_simple,
        iterations=1000
    )

    # Benchmark 2: Large endpoint (50 fields)
    large_endpoint = create_large_endpoint()

    def bench_large():
        extractor.extract_constraints(large_endpoint)

    runner.benchmark(
        name="Extract Constraints - Large Endpoint (50 fields)",
        func=bench_large,
        iterations=500
    )

    # Benchmark 3: Endpoint with natural language documentation
    endpoint_with_docs = simple_endpoint.copy()
    documentation = """
    The user registration endpoint requires an email address (must be valid email format),
    a name (minimum 2 characters, maximum 50 characters), and age (must be at least 18,
    maximum 120). Username is optional but if provided must be between 3 and 20 characters.
    Role must be one of: admin, user, or guest.
    """

    def bench_with_docs():
        extractor.extract_constraints(endpoint_with_docs, documentation)

    runner.benchmark(
        name="Extract Constraints - With Natural Language Docs",
        func=bench_with_docs,
        iterations=500
    )

    # Print summary
    runner.print_summary()

    # Save results
    runner.save_results("benchmarks/results/constraint_extraction.json")

    # Performance thresholds
    print("\n" + "="*80)
    print("PERFORMANCE THRESHOLDS")
    print("="*80)
    print("✅ GOOD: < 10ms per endpoint")
    print("⚠️  OK: 10-50ms per endpoint")
    print("❌ SLOW: > 50ms per endpoint")
    print("="*80)


if __name__ == "__main__":
    main()
