"""
Performance Benchmarks for AutoTest-RL
Measures performance of critical components
"""
import time
import asyncio
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class BenchmarkResult:
    """Result of a single benchmark"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    ops_per_second: float
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self):
        return (
            f"{self.name}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Avg Time: {self.avg_time*1000:.2f}ms\n"
            f"  Min Time: {self.min_time*1000:.2f}ms\n"
            f"  Max Time: {self.max_time*1000:.2f}ms\n"
            f"  Median: {self.median_time*1000:.2f}ms\n"
            f"  Std Dev: {self.std_dev*1000:.2f}ms\n"
            f"  Ops/sec: {self.ops_per_second:.2f}\n"
        )


class BenchmarkRunner:
    """
    Runs performance benchmarks and collects metrics

    Measures:
    - Average execution time
    - Min/Max execution time
    - Median execution time
    - Standard deviation
    - Operations per second
    """

    def __init__(self, warmup_iterations: int = 5):
        self.warmup_iterations = warmup_iterations
        self.results: List[BenchmarkResult] = []

    def benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark a synchronous function

        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            *args, **kwargs: Arguments to pass to function

        Returns:
            BenchmarkResult with metrics
        """
        print(f"\n🔥 Benchmarking: {name}")
        print(f"   Warmup: {self.warmup_iterations} iterations")
        print(f"   Test: {iterations} iterations")

        # Warmup
        for _ in range(self.warmup_iterations):
            func(*args, **kwargs)

        # Actual benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        # Calculate statistics
        total_time = sum(times)
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        ops_per_second = 1.0 / avg_time if avg_time > 0 else 0.0

        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_dev=std_dev,
            ops_per_second=ops_per_second
        )

        self.results.append(result)
        print(f"   ✅ Avg: {avg_time*1000:.2f}ms | Ops/sec: {ops_per_second:.2f}")

        return result

    async def benchmark_async(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark an asynchronous function

        Args:
            name: Benchmark name
            func: Async function to benchmark
            iterations: Number of iterations
            *args, **kwargs: Arguments to pass to function

        Returns:
            BenchmarkResult with metrics
        """
        print(f"\n🔥 Benchmarking (async): {name}")
        print(f"   Warmup: {self.warmup_iterations} iterations")
        print(f"   Test: {iterations} iterations")

        # Warmup
        for _ in range(self.warmup_iterations):
            await func(*args, **kwargs)

        # Actual benchmark
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        # Calculate statistics
        total_time = sum(times)
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        ops_per_second = 1.0 / avg_time if avg_time > 0 else 0.0

        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_dev=std_dev,
            ops_per_second=ops_per_second
        )

        self.results.append(result)
        print(f"   ✅ Avg: {avg_time*1000:.2f}ms | Ops/sec: {ops_per_second:.2f}")

        return result

    def print_summary(self):
        """Print summary of all benchmarks"""
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)

        for result in self.results:
            print(f"\n{result}")

        print("\n" + "="*80)
        print(f"Total Benchmarks: {len(self.results)}")
        print("="*80)

    def save_results(self, filepath: str):
        """Save benchmark results to JSON file"""
        import json

        results_dict = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": [
                {
                    "name": r.name,
                    "iterations": r.iterations,
                    "avg_time_ms": r.avg_time * 1000,
                    "min_time_ms": r.min_time * 1000,
                    "max_time_ms": r.max_time * 1000,
                    "median_time_ms": r.median_time * 1000,
                    "std_dev_ms": r.std_dev * 1000,
                    "ops_per_second": r.ops_per_second
                }
                for r in self.results
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n💾 Results saved to: {filepath}")
