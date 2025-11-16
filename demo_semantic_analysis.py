#!/usr/bin/env python3
"""
Semantic Documentation Analysis Demo
Shows how we extract UNDERSTANDING from natural language API docs
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.analysis.semantic_doc_analyzer import SemanticDocAnalyzer
from src.testing.semantic_test_generator import SemanticTestGenerator


def create_realistic_api_documentation():
    """
    Create realistic API documentation with BOTH technical specs AND prose

    This is what real API docs look like (Stripe, Twilio, GitHub, etc.)
    """
    return """
# Create User API

## POST /api/users

Create a new user account in the system.

### Description

This endpoint creates a new user account. Use this endpoint when you need to
register a new user in your application. This is the first step in the user
onboarding flow.

### Use Cases

Common scenarios for this API include:
- New user registration from a signup form
- Importing users from external systems
- Admin-created accounts for team members
- Bulk user provisioning for enterprise customers

### Authentication

Requires API key authentication. Include your API key in the `X-API-Key` header.

### Request

#### Headers
- `Content-Type`: application/json (required)
- `X-API-Key`: Your API key (required)
- `X-Idempotency-Key`: Optional, for safe retries

#### Body Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | Yes | User's email address (must be unique) |
| name | string | Yes | Full name |
| age | integer | No | User's age (must be 18+) |
| role | string | No | User role (default: 'user', options: 'user', 'admin') |

### Example Request

```bash
// Create a standard user account
curl -X POST https://api.example.com/api/users \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_test_12345" \
  -d '{
    "email": "john.doe@example.com",
    "name": "John Doe",
    "age": 25
  }'
```

### Example Response (201 Created)

```json
{
  "id": "user_abc123",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "age": 25,
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z",
  "status": "active"
}
```

### Best Practices

- Always include the `X-Idempotency-Key` header for retries to prevent duplicate accounts
- Validate email format on the client side before sending
- It's recommended to collect age for compliance (COPPA requires 13+)
- For production, always use HTTPS endpoints

### Common Errors

⚠️ **Warning**: This endpoint will fail if the email is already registered.

Common mistakes to avoid:
- Forgetting to include the X-API-Key header → 401 Unauthorized
- Sending invalid email format → 422 Validation Error
- Creating users under age 18 → 403 Forbidden (business rule)
- Missing required fields → 400 Bad Request

### Error Example (409 Conflict)

```json
// When email already exists
{
  "error": "conflict",
  "message": "Email already registered",
  "code": "EMAIL_EXISTS"
}
```

### Edge Cases

Special scenarios to handle:
- If the user is under 18, the request will be rejected with 403 Forbidden
- For enterprise customers (role='admin'), additional verification may be required
- When creating more than 100 users per hour, rate limiting applies (429 Too Many Requests)
- Users with international characters in names are supported (UTF-8)

### Business Rules

- Email must be unique across the system
- Only system admins can create users with role='admin'
- Users must be at least 18 years old
- Maximum 100 user creations per hour per API key

### Implementation Guide

To implement user creation in your application:

1. First, validate the email and name on the client side
2. Then, make the POST request with required headers
3. Handle the 201 response by saving the user_id
4. If you receive 409, show "Email already registered" message
5. Finally, redirect to the login page or auto-authenticate

### Rate Limits

- 100 requests per hour per API key
- 1000 requests per day per API key

### Versioning

This endpoint is available in API v2 and later. API v1 used `/users/create` (deprecated).
"""


def demonstrate_semantic_extraction():
    """Show how we extract semantic understanding"""

    print("\n" + "=" * 80)
    print("🧠 SEMANTIC DOCUMENTATION ANALYSIS DEMO")
    print("=" * 80)

    # Get realistic API documentation
    doc_text = create_realistic_api_documentation()

    print(f"\n📄 Documentation Length: {len(doc_text)} characters")
    print(f"📄 Documentation Lines: {len(doc_text.split(chr(10)))}")

    # Analyze with semantic analyzer
    analyzer = SemanticDocAnalyzer()

    print("\n🔍 Analyzing documentation...")
    context = analyzer.analyze_endpoint_documentation(
        raw_text=doc_text,
        endpoint_path="/api/users",
        method="POST"
    )

    # Display extracted understanding
    print("\n" + "=" * 80)
    print("📊 EXTRACTED SEMANTIC UNDERSTANDING")
    print("=" * 80)

    print(f"\n🎯 Description:")
    print(f"   {context.description}")

    print(f"\n💡 Use Cases ({len(context.use_cases)}):")
    for i, use_case in enumerate(context.use_cases, 1):
        print(f"   {i}. {use_case[:100]}...")

    print(f"\n📚 Code Examples ({len(context.examples)}):")
    for i, example in enumerate(context.examples, 1):
        print(f"   {i}. {example['type']} - {example['language']}")
        if example['explanation']:
            print(f"      Explanation: {example['explanation']}")
        print(f"      Code preview: {example['code'][:80]}...")

    print(f"\n✅ Best Practices ({len(context.best_practices)}):")
    for i, practice in enumerate(context.best_practices, 1):
        print(f"   {i}. {practice}")

    print(f"\n⚠️  Common Errors ({len(context.common_errors)}):")
    for i, error in enumerate(context.common_errors, 1):
        print(f"   {i}. {error}")

    print(f"\n🔄 Edge Cases ({len(context.edge_cases)}):")
    for i, edge in enumerate(context.edge_cases, 1):
        print(f"   {i}. {edge}")

    print(f"\n📜 Business Rules ({len(context.business_rules)}):")
    for i, rule in enumerate(context.business_rules, 1):
        print(f"   {i}. {rule}")

    print(f"\n📝 Implementation Notes ({len(context.implementation_notes)}):")
    for i, note in enumerate(context.implementation_notes, 1):
        print(f"   {i}. {note}")

    if context.rate_limits:
        print(f"\n⏱️  Rate Limits:")
        print(f"   {context.rate_limits}")

    if context.authentication_details:
        print(f"\n🔐 Authentication:")
        print(f"   {context.authentication_details[:100]}...")

    if context.versioning_info:
        print(f"\n📦 Versioning:")
        print(f"   {context.versioning_info}")

    return context


def demonstrate_semantic_test_generation(context):
    """Show how we generate tests from semantic understanding"""

    print("\n" + "=" * 80)
    print("🧪 SEMANTIC TEST GENERATION")
    print("=" * 80)

    generator = SemanticTestGenerator()

    print("\n🔬 Generating tests from semantic understanding...")
    tests = generator.generate_semantic_tests(context)

    print(f"\n✅ Generated {len(tests)} test cases\n")

    # Group tests by source
    from collections import defaultdict
    tests_by_source = defaultdict(list)
    for test in tests:
        tests_by_source[test['source']].append(test)

    # Display tests by category
    for source, source_tests in tests_by_source.items():
        print(f"\n📋 Tests from {source.replace('_', ' ').title()} ({len(source_tests)}):")
        print("-" * 80)

        for i, test in enumerate(source_tests[:5], 1):  # Show first 5
            print(f"\n   {i}. {test['name']}")
            print(f"      Type: {test['type']}")
            print(f"      Confidence: {test['confidence']}")
            print(f"      Explanation: {test['explanation'][:120]}...")

            if test.get('payload'):
                print(f"      Payload: {test['payload']}")
            if test.get('expected_status'):
                print(f"      Expected Status: {test['expected_status']}")
            if test.get('required_headers'):
                print(f"      Required Headers: {test['required_headers']}")

        if len(source_tests) > 5:
            print(f"\n      ... and {len(source_tests) - 5} more tests")

    # Show generation summary
    print("\n" + "=" * 80)
    print("📊 TEST GENERATION SUMMARY")
    print("=" * 80)

    summary = generator.explain_test_generation(context)

    print(f"\n🎯 Endpoint: {summary['endpoint']}")

    print(f"\n📚 Sources Used:")
    for source, count in summary['sources_used'].items():
        print(f"   {source.replace('_', ' ').title()}: {count}")

    print(f"\n🧪 Test Types Generated:")
    for test_type, count in summary['test_types'].items():
        print(f"   {test_type.replace('_', ' ').title()}: {count}")

    print(f"\n📈 Coverage:")
    for coverage_type, count in summary['coverage'].items():
        print(f"   {coverage_type.replace('_', ' ').title()}: {count}")


def show_comparison():
    """Show the difference between traditional and semantic approaches"""

    print("\n" + "=" * 80)
    print("⚖️  TRADITIONAL vs SEMANTIC APPROACH")
    print("=" * 80)

    print("\n❌ TRADITIONAL APPROACH (Schema-Only):")
    print("-" * 80)
    print("""
Extracts:
- Endpoint: POST /api/users
- Parameters: email (string), name (string), age (integer)
- Response: 201 Created

Generates 3 tests:
1. Valid request with all fields
2. Missing required field (email)
3. Invalid type (age as string)

Missing:
- No understanding of WHY age must be 18+
- No tests for email uniqueness (business rule)
- No tests for admin role restriction
- No tests for rate limiting
- No tests based on documented examples
- No tests for documented error scenarios
""")

    print("\n✅ SEMANTIC APPROACH (Full Understanding):")
    print("-" * 80)
    print("""
Extracts:
- Technical specs (same as traditional)
- PLUS 4 documented use cases
- PLUS 2 code examples (request + error)
- PLUS 4 best practices
- PLUS 4 common errors
- PLUS 4 edge cases
- PLUS 4 business rules
- PLUS 5 implementation steps

Generates 20+ tests:
1. Tests from examples (2)
   - Standard user creation (from curl example)
   - Duplicate email error (from error example)

2. Tests from use cases (4)
   - Signup form registration
   - External system import
   - Admin account creation
   - Bulk provisioning

3. Tests from best practices (4)
   - With idempotency key
   - Email validation
   - HTTPS endpoint
   - Age compliance

4. Tests from common errors (4)
   - Missing API key → 401
   - Invalid email → 422
   - Under 18 → 403
   - Missing required fields → 400

5. Tests from edge cases (4)
   - Age boundary (17, 18, 19)
   - Admin role creation
   - Rate limit (100+ requests)
   - International characters

6. Tests from business rules (4)
   - Email uniqueness check
   - Admin-only role assignment
   - Age minimum enforcement
   - Rate limit validation

Result: 10x more coverage, 100% aligned with actual documentation
""")


def main():
    """Run the demo"""

    # Step 1: Extract semantic understanding
    context = demonstrate_semantic_extraction()

    # Step 2: Generate tests from understanding
    demonstrate_semantic_test_generation(context)

    # Step 3: Show the difference
    show_comparison()

    print("\n" + "=" * 80)
    print("🎉 DEMO COMPLETE")
    print("=" * 80)

    print("""
🔑 Key Takeaway:

Traditional parsers extract STRUCTURE (schemas, parameters).
Semantic analyzers extract UNDERSTANDING (why, when, how).

With semantic analysis, tests reflect REAL usage patterns from documentation:
- Examples become golden test cases
- Best practices become validation rules
- Common errors become negative tests
- Edge cases become boundary tests
- Business rules become constraint validation

This is how we go from "testing the schema" to "testing the documented behavior".
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
