# Performance Benchmarks

Comprehensive performance benchmarks for AutoTest-RL critical components.

## 📊 Overview

Benchmarks measure performance of:
- **Constraint Extraction** - Parsing API docs and extracting validation rules
- **Test Generation** - Creating comprehensive test suites
- **Schema Validation** - Validating responses against OpenAPI schemas

## 🚀 Quick Start

```bash
# Run all benchmarks
./benchmarks/run_benchmarks.sh

# Run specific benchmark
./benchmarks/run_benchmarks.sh constraint
./benchmarks/run_benchmarks.sh generation
./benchmarks/run_benchmarks.sh validation
```

## 📁 Structure

```
benchmarks/
├── benchmark_runner.py           # Core benchmark infrastructure
├── bench_constraint_extraction.py  # Constraint extraction benchmarks
├── bench_test_generation.py      # Test generation benchmarks
├── bench_schema_validation.py    # Schema validation benchmarks
├── run_benchmarks.sh             # Benchmark runner script
├── results/                      # JSON results (gitignored)
│   ├── constraint_extraction.json
│   ├── test_generation.json
│   └── schema_validation.json
└── README.md                     # This file
```

## 📈 Benchmarks

### 1. Constraint Extraction

**What it measures:** Time to extract validation constraints from API documentation

**Scenarios:**
- Simple endpoint (6 fields)
- Large endpoint (50 fields)
- Natural language documentation parsing

**Performance Thresholds:**
- ✅ GOOD: < 10ms per endpoint
- ⚠️  OK: 10-50ms per endpoint
- ❌ SLOW: > 50ms per endpoint

**Run:**
```bash
python benchmarks/bench_constraint_extraction.py
```

### 2. Test Generation

**What it measures:** Time to generate comprehensive test suites

**Scenarios:**
- Boundary tests (3 parameters)
- Boundary tests (20 parameters)
- Combinatorial tests (2-way coverage)

**Performance Thresholds:**
- ✅ GOOD: < 50ms per endpoint
- ⚠️  OK: 50-200ms per endpoint
- ❌ SLOW: > 200ms per endpoint

**Run:**
```bash
python benchmarks/bench_test_generation.py
```

### 3. Schema Validation

**What it measures:** Time to validate API responses against schemas

**Scenarios:**
- Simple schema (permissive mode)
- Simple schema (strict mode)
- Large object (100 fields)
- Deeply nested object
- Validation with violations

**Performance Thresholds:**
- ✅ GOOD: < 5ms per validation
- ⚠️  OK: 5-20ms per validation
- ❌ SLOW: > 20ms per validation

**Run:**
```bash
python benchmarks/bench_schema_validation.py
```

## 📊 Metrics Collected

For each benchmark, we collect:
- **Average Time** - Mean execution time
- **Min/Max Time** - Fastest and slowest runs
- **Median Time** - Middle value (50th percentile)
- **Standard Deviation** - Consistency measure
- **Operations/Second** - Throughput metric

## 🔍 Sample Output

```
🔥 Benchmarking: Extract Constraints - Simple Endpoint (6 fields)
   Warmup: 10 iterations
   Test: 1000 iterations
   ✅ Avg: 4.23ms | Ops/sec: 236.41

================================================================================
BENCHMARK SUMMARY
================================================================================

Extract Constraints - Simple Endpoint (6 fields):
  Iterations: 1000
  Avg Time: 4.23ms
  Min Time: 3.12ms
  Max Time: 8.45ms
  Median: 4.10ms
  Std Dev: 0.87ms
  Ops/sec: 236.41

💾 Results saved to: benchmarks/results/constraint_extraction.json
```

## 📁 Results Format

Results are saved as JSON:

```json
{
  "timestamp": "2025-01-18T15:30:00.123456",
  "benchmarks": [
    {
      "name": "Extract Constraints - Simple Endpoint (6 fields)",
      "iterations": 1000,
      "avg_time_ms": 4.23,
      "min_time_ms": 3.12,
      "max_time_ms": 8.45,
      "median_time_ms": 4.10,
      "std_dev_ms": 0.87,
      "ops_per_second": 236.41
    }
  ]
}
```

## 🎯 Performance Goals

### Current Performance (Target)
- Constraint Extraction: **< 10ms** per endpoint
- Test Generation: **< 50ms** per endpoint
- Schema Validation: **< 5ms** per validation

### Scalability Goals
- Handle **100+ endpoints** in < 1 second
- Generate **1000+ tests** in < 5 seconds
- Validate **100+ responses** in < 1 second

## 🔧 Optimization Opportunities

Based on benchmarks, these are priority optimizations:

1. **Caching** (Phase 7.2)
   - Cache parsed OpenAPI specs
   - Cache extracted constraints
   - Cache generated tests for repeated endpoints

2. **Parallel Processing** (Phase 7.3)
   - Generate tests in parallel
   - Validate responses concurrently
   - Batch constraint extraction

3. **Database** (Phase 7.1)
   - Persist parsed documentation
   - Store test results
   - Index for fast lookups

## 📊 Baseline Results

Initial baseline (to be updated after running):

```
Component               | Avg Time  | Ops/sec | Status
------------------------|-----------|---------|--------
Constraint Extraction   | TBD       | TBD     | ⏳
Test Generation         | TBD       | TBD     | ⏳
Schema Validation       | TBD       | TBD     | ⏳
```

## 🚀 Running Benchmarks in CI

Add to GitHub Actions:

```yaml
- name: Run Benchmarks
  run: |
    ./benchmarks/run_benchmarks.sh

- name: Upload Results
  uses: actions/upload-artifact@v2
  with:
    name: benchmark-results
    path: benchmarks/results/
```

## 📈 Monitoring Performance

Track performance over time:

```bash
# Run benchmarks
./benchmarks/run_benchmarks.sh

# Compare with previous results
diff benchmarks/results/constraint_extraction.json \
     benchmarks/results_previous/constraint_extraction.json
```

## 🛠️ Adding New Benchmarks

1. Create new benchmark file: `benchmarks/bench_new_component.py`
2. Use `BenchmarkRunner`:

```python
from benchmarks.benchmark_runner import BenchmarkRunner

runner = BenchmarkRunner(warmup_iterations=10)

def my_function():
    # Code to benchmark
    pass

runner.benchmark(
    name="My Benchmark",
    func=my_function,
    iterations=1000
)

runner.print_summary()
runner.save_results("benchmarks/results/my_benchmark.json")
```

3. Add to `run_benchmarks.sh`

## 🎯 Next Steps

After establishing baselines:
1. Identify bottlenecks
2. Implement optimizations (Phase 7)
3. Re-run benchmarks to measure improvements
4. Set up continuous performance monitoring

---

**Phase 6.3 Complete** - Performance benchmarking infrastructure ready!
