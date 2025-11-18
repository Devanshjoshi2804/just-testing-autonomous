#!/bin/bash
#
# Test Runner Script for AutoTest-RL
# Runs unit tests, integration tests, and generates coverage reports
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "AutoTest-RL Test Suite Runner"
echo "======================================================================"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "Install test dependencies: pip install -r requirements-test.txt"
    exit 1
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"

# Function to run tests
run_tests() {
    local test_path="$1"
    local description="$2"
    local markers="${3:-}"

    echo ""
    echo "======================================================================"
    echo -e "${GREEN}Running: $description${NC}"
    echo "======================================================================"

    if [ -n "$markers" ]; then
        pytest "$test_path" -m "$markers" -v --tb=short
    else
        pytest "$test_path" -v --tb=short
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $description passed${NC}"
    else
        echo -e "${RED}❌ $description failed${NC}"
        return 1
    fi
}

# Main test execution
case "$TEST_TYPE" in
    unit)
        echo -e "${YELLOW}Running unit tests only${NC}"
        run_tests "tests/unit/" "Unit Tests" "unit"
        ;;

    integration)
        echo -e "${YELLOW}Running integration tests only${NC}"
        run_tests "tests/integration/" "Integration Tests" "integration"
        ;;

    fast)
        echo -e "${YELLOW}Running fast tests only (excluding slow)${NC}"
        pytest tests/ -m "not slow" -v --tb=short
        ;;

    coverage)
        echo -e "${YELLOW}Running all tests with coverage report${NC}"
        pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v

        echo ""
        echo "======================================================================"
        echo -e "${GREEN}Coverage report generated${NC}"
        echo "======================================================================"
        echo "HTML report: htmlcov/index.html"
        echo "View with: open htmlcov/index.html  (macOS)"
        echo "       or: xdg-open htmlcov/index.html  (Linux)"
        ;;

    smoke)
        echo -e "${YELLOW}Running smoke tests${NC}"
        run_tests "tests/" "Smoke Tests" "smoke"
        ;;

    all)
        echo -e "${YELLOW}Running all tests${NC}"

        # Run unit tests
        run_tests "tests/unit/" "Unit Tests" "unit"

        # Run integration tests
        echo ""
        read -p "Run integration tests (may require network)? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_tests "tests/integration/" "Integration Tests" "integration"
        else
            echo -e "${YELLOW}⏭️  Skipping integration tests${NC}"
        fi

        # Generate coverage
        echo ""
        echo "======================================================================"
        echo -e "${GREEN}Generating coverage report${NC}"
        echo "======================================================================"
        pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing
        ;;

    help|--help|-h)
        echo "Usage: ./run_tests.sh [TEST_TYPE]"
        echo ""
        echo "TEST_TYPE options:"
        echo "  all          - Run all tests (unit + integration)"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests only"
        echo "  fast         - Run fast tests only (exclude slow tests)"
        echo "  coverage     - Run all tests with coverage report"
        echo "  smoke        - Run smoke tests only"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh              # Run all tests"
        echo "  ./run_tests.sh unit         # Unit tests only"
        echo "  ./run_tests.sh coverage     # With coverage report"
        exit 0
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run './run_tests.sh help' for usage"
        exit 1
        ;;
esac

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Test run complete!${NC}"
echo "======================================================================"
