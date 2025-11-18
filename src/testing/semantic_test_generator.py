"""
Semantic Test Generator
Generates tests based on natural language understanding from documentation
"""
from typing import Dict, List, Any
from src.analysis.semantic_doc_analyzer import DocumentationContext

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    logger = MockLogger()


class SemanticTestGenerator:
    """
    Generates intelligent tests using BOTH technical specs AND natural language understanding

    Traditional test generators only use:
    - Endpoint path
    - Request schema
    - Parameter types

    Semantic test generator ALSO uses:
    - Use cases from documentation
    - Examples with explanations
    - Best practices
    - Common errors to avoid
    - Edge cases mentioned in prose
    - Business rules extracted from text

    Result: Tests that reflect REAL usage, not just schema validation.
    """

    def __init__(self, llm_client=None):
        """
        Initialize semantic test generator

        Args:
            llm_client: LLM for intelligent test generation
        """
        self.llm = llm_client

    def generate_semantic_tests(
        self,
        context: DocumentationContext
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive tests from semantic understanding

        Args:
            context: Rich documentation context

        Returns:
            List of test cases with explanations
        """
        tests = []

        logger.info(
            f"Generating semantic tests for {context.method} {context.endpoint}"
        )

        # 1. Tests from examples (GOLDEN SOURCE!)
        tests.extend(self._tests_from_examples(context))

        # 2. Tests from use cases
        tests.extend(self._tests_from_use_cases(context))

        # 3. Tests from best practices
        tests.extend(self._tests_from_best_practices(context))

        # 4. Tests from common errors (negative tests!)
        tests.extend(self._tests_from_common_errors(context))

        # 5. Tests from edge cases
        tests.extend(self._tests_from_edge_cases(context))

        # 6. Tests from business rules
        tests.extend(self._tests_from_business_rules(context))

        logger.info(f"Generated {len(tests)} semantic test cases")

        return tests

    def _tests_from_examples(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate tests from code examples in documentation

        This is GOLDEN - examples show real usage!
        """
        tests = []

        for example in context.examples:
            if example['type'] == 'request_with_body':
                # Extract payload from example
                payload = self._extract_payload_from_code(example['code'])

                if payload:
                    tests.append({
                        'name': f"Example: {example['explanation'] or 'Documented usage'}",
                        'type': 'positive',
                        'source': 'documentation_example',
                        'payload': payload,
                        'expected_status': 200,
                        'explanation': (
                            f"This test uses the exact example from documentation: "
                            f"{example['explanation']}"
                        ),
                        'confidence': 'HIGH',  # Examples are authoritative
                    })

            elif example['type'] == 'error_example':
                # Extract error scenario
                tests.append({
                    'name': f"Error example: {example['explanation']}",
                    'type': 'negative',
                    'source': 'documentation_error_example',
                    'payload': self._extract_payload_from_code(example['code']),
                    'expected_status': self._extract_error_code(example['code']),
                    'explanation': (
                        f"This test verifies the error handling described in docs: "
                        f"{example['explanation']}"
                    ),
                    'confidence': 'HIGH',
                })

        return tests

    def _tests_from_use_cases(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate tests from documented use cases

        Example use case: "Use this endpoint when creating a new user account"
        → Generate test for user account creation scenario
        """
        tests = []

        for use_case in context.use_cases:
            # Use LLM to understand use case and generate test
            test = {
                'name': f"Use case: {use_case[:80]}",
                'type': 'positive',
                'source': 'use_case',
                'scenario': use_case,
                'explanation': (
                    f"This test covers the documented use case: {use_case}"
                ),
                'confidence': 'MEDIUM',
                # Payload would be generated by LLM based on use case
                'needs_llm_generation': True,
            }
            tests.append(test)

        return tests

    def _tests_from_best_practices(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate tests that verify best practices are followed

        Example: "Always include X-Request-ID header"
        → Generate test that includes X-Request-ID
        """
        tests = []

        for practice in context.best_practices:
            if 'header' in practice.lower():
                # Extract header name
                header_match = self._extract_header_name(practice)

                if header_match:
                    tests.append({
                        'name': f"Best practice: {practice[:80]}",
                        'type': 'positive',
                        'source': 'best_practice',
                        'required_headers': {header_match: 'test-value'},
                        'explanation': (
                            f"This test follows the documented best practice: "
                            f"{practice}"
                        ),
                        'confidence': 'MEDIUM',
                    })

            elif 'parameter' in practice.lower() or 'field' in practice.lower():
                tests.append({
                    'name': f"Best practice: {practice[:80]}",
                    'type': 'positive',
                    'source': 'best_practice',
                    'scenario': practice,
                    'explanation': (
                        f"This test implements the recommended practice: "
                        f"{practice}"
                    ),
                    'confidence': 'MEDIUM',
                    'needs_llm_generation': True,
                })

        return tests

    def _tests_from_common_errors(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate NEGATIVE tests from documented common errors

        Example: "This will fail if user_id is missing"
        → Generate test that omits user_id and expects failure
        """
        tests = []

        for error in context.common_errors:
            # This is a NEGATIVE test - we expect it to fail
            tests.append({
                'name': f"Error scenario: {error[:80]}",
                'type': 'negative',
                'source': 'documented_error',
                'scenario': error,
                'expected_status': self._infer_error_status(error),
                'explanation': (
                    f"This test verifies the documented error condition: "
                    f"{error}"
                ),
                'confidence': 'HIGH',  # Documented errors are reliable
                'needs_llm_generation': True,
            })

        return tests

    def _tests_from_edge_cases(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate tests from documented edge cases

        Example: "For pagination beyond 100 items, use cursor-based pagination"
        → Generate test with >100 items
        """
        tests = []

        for edge_case in context.edge_cases:
            tests.append({
                'name': f"Edge case: {edge_case[:80]}",
                'type': 'boundary',
                'source': 'documented_edge_case',
                'scenario': edge_case,
                'explanation': (
                    f"This test covers the documented edge case: "
                    f"{edge_case}"
                ),
                'confidence': 'MEDIUM',
                'needs_llm_generation': True,
            })

        return tests

    def _tests_from_business_rules(self, context: DocumentationContext) -> List[Dict]:
        """
        Generate tests from extracted business rules

        Example: "Only admins can delete users"
        → Generate test with non-admin user expecting 403
        """
        tests = []

        for rule in context.business_rules:
            if 'only' in rule.lower() or 'must' in rule.lower():
                # This is a constraint to test
                tests.append({
                    'name': f"Business rule: {rule[:80]}",
                    'type': 'negative',  # Test the constraint
                    'source': 'business_rule',
                    'scenario': rule,
                    'expected_status': 403,  # Usually authorization
                    'explanation': (
                        f"This test verifies the business rule: {rule}"
                    ),
                    'confidence': 'HIGH',
                    'needs_llm_generation': True,
                })

            elif 'limit' in rule.lower() or 'maximum' in rule.lower():
                # This is a boundary condition
                tests.append({
                    'name': f"Limit test: {rule[:80]}",
                    'type': 'boundary',
                    'source': 'business_rule',
                    'scenario': rule,
                    'explanation': (
                        f"This test verifies the documented limit: {rule}"
                    ),
                    'confidence': 'HIGH',
                    'needs_llm_generation': True,
                })

        return tests

    def _extract_payload_from_code(self, code: str) -> Dict:
        """Extract JSON payload from code example"""
        import json
        import re

        # Try to find JSON objects in code
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, code, re.DOTALL)

        for match in matches:
            try:
                payload = json.loads(match)
                # Skip response objects (usually have 'id' field)
                if 'id' not in payload or len(payload) > 2:
                    return payload
            except:
                continue

        return {}

    def _extract_error_code(self, code: str) -> int:
        """Extract HTTP error code from example"""
        import re

        # Look for status codes
        code_match = re.search(r'\b(4\d{2}|5\d{2})\b', code)
        if code_match:
            return int(code_match.group(1))

        # Default to 400 for error examples
        return 400

    def _extract_header_name(self, practice: str) -> str:
        """Extract header name from best practice text"""
        import re

        # Look for header names (usually capitalized or X-prefixed)
        header_match = re.search(
            r'(?:header[:\s]+)?([A-Z][a-z-]+(?:-[A-Z][a-z-]+)*|X-[A-Z][a-z-]+(?:-[A-Z][a-z-]+)*)',
            practice
        )

        if header_match:
            return header_match.group(1)

        return ""

    def _infer_error_status(self, error: str) -> int:
        """Infer expected HTTP status from error description"""
        error_lower = error.lower()

        if 'not found' in error_lower or 'does not exist' in error_lower:
            return 404
        elif 'unauthorized' in error_lower or 'not authenticated' in error_lower:
            return 401
        elif 'forbidden' in error_lower or 'not allowed' in error_lower:
            return 403
        elif 'invalid' in error_lower or 'validation' in error_lower:
            return 422
        elif 'conflict' in error_lower or 'already exists' in error_lower:
            return 409
        elif 'rate limit' in error_lower or 'too many' in error_lower:
            return 429
        else:
            return 400  # Default bad request

    def explain_test_generation(self, context: DocumentationContext) -> Dict:
        """
        Explain how tests were generated from documentation

        This helps developers understand WHY each test exists
        """
        return {
            'endpoint': f"{context.method} {context.endpoint}",
            'sources_used': {
                'examples': len(context.examples),
                'use_cases': len(context.use_cases),
                'best_practices': len(context.best_practices),
                'common_errors': len(context.common_errors),
                'edge_cases': len(context.edge_cases),
                'business_rules': len(context.business_rules),
            },
            'test_types': {
                'positive_from_examples': len([e for e in context.examples if e['type'] != 'error_example']),
                'negative_from_errors': len(context.common_errors),
                'boundary_from_edge_cases': len(context.edge_cases),
                'business_rule_validation': len(context.business_rules),
            },
            'coverage': {
                'documented_scenarios': len(context.use_cases),
                'error_scenarios': len(context.common_errors),
                'edge_scenarios': len(context.edge_cases),
            }
        }
