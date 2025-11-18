# API Documentation for Testing

This directory contains API documentation files that will be tested by AutoTest-RL.

## Supported Formats

### 1. **PDF Files** (`.pdf`)
- API documentation in PDF format
- The system will extract endpoints, parameters, constraints, and descriptions
- Place your API PDF documentation files here

### 2. **OpenAPI Specifications** (`.json`, `.yaml`, `.yml`)
- OpenAPI 3.0.x specifications
- Swagger 2.0 specifications
- Complete endpoint definitions with schemas

### 3. **Markdown Documentation** (`.md`) - Future support
- API documentation in markdown format

## Sample Files Included

- **sample-users-api.yaml** - A complete OpenAPI 3.0 specification for a user management API
  - Demonstrates typical CRUD operations
  - Shows proper constraint definitions
  - Includes error response documentation
  - Has authentication requirements
  - Contains validation rules

## How to Add Your Documentation

### For OpenAPI/Swagger Specs:

1. Place your `.json` or `.yaml` files in this directory
2. Ensure they follow OpenAPI 3.0.x or Swagger 2.0 format
3. Run the test script: `python test_real_apis.py`

### For PDF Documentation:

1. Place your PDF files in this directory
2. Ensure PDFs contain:
   - Endpoint paths (e.g., `/api/users`)
   - HTTP methods (GET, POST, PUT, DELETE, PATCH)
   - Parameter descriptions
   - Response examples
   - Error codes and messages
3. Run the test script: `python test_real_apis.py`

## Running the Tests

From the project root directory:

```bash
# Run the full pipeline on all documentation
python test_real_apis.py
```

The script will:
1. **Discover** all documentation files in this directory
2. **Parse** each file to extract API structure
3. **Extract constraints** from documentation
4. **Generate tests** using all testing strategies
5. **Save results** to `data/test-results/` and `data/parsed-docs/`

## Output Structure

After running tests, you'll find:

```
data/
├── test-results/
│   └── test_report_YYYYMMDD_HHMMSS.json
└── parsed-docs/
    ├── {filename}_parsed.json       # Parsed API structure
    ├── {filename}_constraints.json  # Extracted constraints
    └── {filename}_tests.json        # Generated test cases
```

## What Gets Tested

For each endpoint, the system generates:

1. **Positive Tests**
   - Valid requests with proper data
   - Boundary values for numeric fields
   - Valid format examples (emails, UUIDs, dates)

2. **Negative Tests**
   - Missing required fields
   - Invalid data types
   - Out-of-range values
   - Invalid formats

3. **Security Tests**
   - SQL injection attempts
   - XSS payloads
   - OWASP Top 10 vulnerabilities
   - Authentication/authorization bypasses

4. **Edge Cases**
   - Minimum/maximum boundaries
   - Empty strings
   - Null values
   - Special characters

5. **Workflow Tests**
   - Multi-step API flows
   - Dependent requests
   - State transitions

## Expected Test Count

For a typical API:
- **Simple endpoint** (GET with no params): ~15 tests
- **CRUD endpoint** (with validation): ~40-50 tests
- **Complex endpoint** (multiple params, auth): ~60-80 tests

The sample-users-api.yaml will generate **200+ comprehensive tests**.

## Tips for Best Results

### For OpenAPI Specs:
- Include detailed descriptions
- Define all constraints (min, max, minLength, maxLength, format, enum)
- Document all possible response codes
- Include example values
- Define proper error schemas

### For PDF Documentation:
- Use clear section headers
- Include code examples with actual values
- Document validation rules explicitly
- List all error codes with descriptions
- Include parameter tables with types and constraints

## Troubleshooting

### No endpoints found:
- Check if PDF has machine-readable text (not scanned images)
- Verify OpenAPI spec follows correct format
- Look for parsing errors in logs

### Tests not comprehensive:
- Add more constraint details to documentation
- Include examples and validation rules
- Document error scenarios explicitly

### Parsing errors:
- Ensure valid JSON/YAML syntax
- Check PDF is not password-protected
- Verify file encoding is UTF-8

## Example: Well-Documented Constraint

Good documentation that will generate comprehensive tests:

```yaml
email:
  type: string
  format: email
  minLength: 5
  maxLength: 100
  pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  description: User's email address (must be unique)
  example: "john.doe@example.com"
```

This will generate tests for:
- Valid emails
- Invalid email formats
- Length boundaries (4, 5, 100, 101 characters)
- Special characters
- SQL injection in email field
- XSS in email field

## Next Steps

1. Add your API documentation files to this directory
2. Run `python test_real_apis.py`
3. Review generated tests in `data/parsed-docs/`
4. Check test results in `data/test-results/`
5. Iterate on documentation to improve test coverage
