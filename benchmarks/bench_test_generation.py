"""
Benchmarks for Test Generation
Tests performance of generating comprehensive test suites
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.benchmark_runner import BenchmarkRunner
from src.generators.boundary_test_generator import BoundaryTestGenerator
from src.generators.combinatorial_test_generator import CombinatorialTestGenerator
from unittest.mock import Mock


def create_sample_constraints():
    """Create sample constraints for testing"""
    return {
        "page": {
            "type": "integer",
            "constraints": [
                {"constraint_type": "min_value", "value": 1},
                {"constraint_type": "max_value", "value": 100}
            ]
        },
        "limit": {
            "type": "integer",
            "constraints": [
                {"constraint_type": "min_value", "value": 1},
                {"constraint_type": "max_value", "value": 50}
            ]
        },
        "search": {
            "type": "string",
            "constraints": [
                {"constraint_type": "min_length", "value": 2},
                {"constraint_type": "max_length", "value": 100}
            ]
        }
    }


def create_large_constraints():
    """Create constraints with many parameters"""
    constraints = {}
    for i in range(20):
        constraints[f"param_{i}"] = {
            "type": "integer" if i % 2 == 0 else "string",
            "constraints": [
                {"constraint_type": "min_value" if i % 2 == 0 else "min_length", "value": 1},
                {"constraint_type": "max_value" if i % 2 == 0 else "max_length", "value": 100}
            ]
        }
    return constraints


def main():
    """Run test generation benchmarks"""
    print("="*80)
    print("TEST GENERATION BENCHMARKS")
    print("="*80)

    runner = BenchmarkRunner(warmup_iterations=5)

    # Benchmark 1: Boundary Test Generation (3 parameters)
    boundary_gen = BoundaryTestGenerator()
    endpoint = {
        "path": "/api/users",
        "method": "GET",
        "parameters": [
            {"name": "page", "in": "query"},
            {"name": "limit", "in": "query"},
            {"name": "search", "in": "query"}
        ]
    }
    constraints = create_sample_constraints()

    def bench_boundary_simple():
        boundary_gen.generate_boundary_test_suite(endpoint, constraints)

    runner.benchmark(
        name="Boundary Test Generation - 3 Parameters",
        func=bench_boundary_simple,
        iterations=500
    )

    # Benchmark 2: Boundary Test Generation (20 parameters)
    large_endpoint = {
        "path": "/api/complex",
        "method": "POST",
        "parameters": [{"name": f"param_{i}", "in": "body"} for i in range(20)]
    }
    large_constraints = create_large_constraints()

    def bench_boundary_large():
        boundary_gen.generate_boundary_test_suite(large_endpoint, large_constraints)

    runner.benchmark(
        name="Boundary Test Generation - 20 Parameters",
        func=bench_boundary_large,
        iterations=100
    )

    # Benchmark 3: Combinatorial Test Generation
    combo_gen = CombinatorialTestGenerator()

    def bench_combinatorial():
        combo_gen.generate_combinatorial_tests(endpoint, constraints, strength=2)

    runner.benchmark(
        name="Combinatorial Test Generation - 2-way Coverage",
        func=bench_combinatorial,
        iterations=100
    )

    # Print summary
    runner.print_summary()

    # Save results
    runner.save_results("benchmarks/results/test_generation.json")

    # Performance thresholds
    print("\n" + "="*80)
    print("PERFORMANCE THRESHOLDS")
    print("="*80)
    print("✅ GOOD: < 50ms per endpoint")
    print("⚠️  OK: 50-200ms per endpoint")
    print("❌ SLOW: > 200ms per endpoint")
    print("="*80)


if __name__ == "__main__":
    main()
