# AutoTest-RL Test Suite

Comprehensive unit and integration tests for the AutoTest-RL system.

## 📁 Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_constraint_extractor.py
│   ├── test_boundary_test_generator.py
│   └── test_schema_validator.py
├── integration/             # Integration tests (coming soon)
├── fixtures/                # Test fixtures and data
├── conftest.py             # Shared pytest fixtures
└── README.md               # This file
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_constraint_extractor.py

# Run specific test
pytest tests/unit/test_constraint_extractor.py::TestConstraintExtractor::test_extract_min_value
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Types

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

## 📊 Test Coverage Goals

- **Overall Coverage:** 70%+
- **Critical Components:** 85%+
  - Constraint Extractor
  - Test Generators
  - Schema Validator
  - Coverage Tracker

## 🧪 Writing Tests

### Test File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`

### Test Function Naming

```python
def test_<what_is_being_tested>_<expected_outcome>():
    """Clear description of what this test verifies"""
    # Arrange
    # Act
    # Assert
```

### Using Fixtures

```python
@pytest.mark.unit
class TestMyComponent:
    @pytest.fixture
    def component(self):
        """Create component instance for tests"""
        return MyComponent()

    def test_something(self, component):
        """Test uses the fixture"""
        result = component.do_something()
        assert result is not None
```

### Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    """Fast, isolated unit test"""
    pass

@pytest.mark.integration
def test_integration_flow():
    """Test that requires multiple components"""
    pass

@pytest.mark.slow
def test_expensive_operation():
    """Test that takes > 1 second"""
    pass

@pytest.mark.requires_llm
def test_with_llm():
    """Test that needs LLM service running"""
    pass
```

## 🔧 Configuration

### pytest.ini

Configuration in `pytest.ini`:
- Test discovery patterns
- Coverage settings (70% minimum)
- Markers definition
- Logging configuration

### conftest.py

Shared fixtures:
- `test_settings` - Test configuration
- `mock_settings` - Mocked settings
- `sample_endpoint` - Sample API endpoint data
- `sample_constraints` - Sample constraint data
- `mock_llm_client` - Mocked LLM client
- `mock_chromadb` - Mocked ChromaDB
- `mock_redis` - Mocked Redis

## 📝 Test Examples

### Unit Test Example

```python
@pytest.mark.unit
class TestConstraintExtractor:
    def test_extract_min_value(self, extractor):
        """Test extracting minimum value constraint"""
        documentation = "The page parameter must be at least 1"
        endpoint = {
            "parameters": {
                "page": {
                    "type": "integer",
                    "description": documentation
                }
            }
        }

        constraints = extractor.extract_constraints(endpoint, documentation)

        assert "page" in constraints
        assert constraints["page"].has_constraint(ConstraintType.MIN_VALUE)
```

### Async Test Example

```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_function():
    """Test async function"""
    result = await some_async_function()
    assert result is not None
```

### Parameterized Test Example

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    """Test with multiple inputs"""
    assert multiply_by_two(input) == expected
```

## 🐛 Debugging Tests

### Run with Print Statements

```bash
# See print output
pytest -s

# Very verbose
pytest -vv

# Show local variables on failure
pytest -l
```

### Run Only Failed Tests

```bash
# Rerun last failed tests
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Use Debugger

```python
def test_with_debugging():
    """Test with debugger"""
    import pdb; pdb.set_trace()
    # ... test code
```

## 🚀 Continuous Integration

Tests run automatically on:
- Every commit (via pre-commit hook)
- Every pull request
- Before deployment

### CI Configuration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements-test.txt
      - run: pytest
```

## 📈 Test Metrics

Check current coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

Generate HTML report:
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## ✅ Best Practices

1. **Test Isolation:** Each test should be independent
2. **Fast Tests:** Unit tests should run in <100ms each
3. **Clear Names:** Test names should describe what they verify
4. **One Assert:** Prefer one logical assertion per test
5. **Use Fixtures:** Reuse common setup code
6. **Mock External:** Mock external services (LLM, DB, APIs)
7. **Test Edge Cases:** Test boundaries, errors, empty inputs
8. **Document:** Add docstrings explaining what test verifies

## 🔍 Code Coverage

### Current Coverage (Phase 6.1)

- ✅ **ConstraintExtractor:** 95%+ (40+ tests)
- ✅ **BoundaryTestGenerator:** 90%+ (35+ tests)
- ✅ **SchemaValidator:** 95%+ (50+ tests)
- ⏳ **CoverageTracker:** Pending
- ⏳ **Other components:** In progress

### Coverage Report

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html

# XML report (for CI)
pytest --cov=src --cov-report=xml
```

## 🎯 Next Steps

1. ✅ Phase 6.1: Unit tests (In Progress)
2. ⏳ Phase 6.2: Integration tests
3. ⏳ Phase 6.3: Performance benchmarks
4. ⏳ CI/CD integration
5. ⏳ Test against public APIs

## 📚 Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Goal:** Achieve 70%+ code coverage with high-quality, maintainable tests
