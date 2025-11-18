#!/bin/bash
#
# Run Performance Benchmarks for AutoTest-RL
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "AutoTest-RL Performance Benchmarks"
echo "======================================================================"
echo ""

# Create results directory
mkdir -p benchmarks/results

# Parse command line
BENCHMARK="${1:-all}"

case "$BENCHMARK" in
    constraint)
        echo -e "${YELLOW}Running Constraint Extraction Benchmarks${NC}"
        python benchmarks/bench_constraint_extraction.py
        ;;

    generation)
        echo -e "${YELLOW}Running Test Generation Benchmarks${NC}"
        python benchmarks/bench_test_generation.py
        ;;

    validation)
        echo -e "${YELLOW}Running Schema Validation Benchmarks${NC}"
        python benchmarks/bench_schema_validation.py
        ;;

    all)
        echo -e "${YELLOW}Running All Benchmarks${NC}"
        echo ""

        echo "1/3: Constraint Extraction"
        python benchmarks/bench_constraint_extraction.py

        echo ""
        echo "2/3: Test Generation"
        python benchmarks/bench_test_generation.py

        echo ""
        echo "3/3: Schema Validation"
        python benchmarks/bench_schema_validation.py

        echo ""
        echo "======================================================================"
        echo -e "${GREEN}All Benchmarks Complete!${NC}"
        echo "======================================================================"
        echo "Results saved to: benchmarks/results/"
        echo ""
        ;;

    help|--help|-h)
        echo "Usage: ./benchmarks/run_benchmarks.sh [BENCHMARK]"
        echo ""
        echo "BENCHMARK options:"
        echo "  all          - Run all benchmarks (default)"
        echo "  constraint   - Constraint extraction benchmarks"
        echo "  generation   - Test generation benchmarks"
        echo "  validation   - Schema validation benchmarks"
        echo "  help         - Show this help"
        echo ""
        exit 0
        ;;

    *)
        echo "Unknown benchmark: $BENCHMARK"
        echo "Run './benchmarks/run_benchmarks.sh help' for usage"
        exit 1
        ;;
esac
