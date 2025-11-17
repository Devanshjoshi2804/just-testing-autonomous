"""
Enhanced Test Generator with Semantic Understanding
Combines LLM-based generation with semantic test generation from documentation
"""
import json
from typing import Dict, Any, List, Optional

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()

from src.agents.test_generator import TestGenerator
from src.testing.semantic_test_generator import SemanticTestGenerator
from src.testing.mutation_test_generator import MutationTestGenerator
from src.analysis.semantic_doc_analyzer import DocumentationContext
from src.generators.combinatorial_test_generator import CombinatorialTestGenerator
from src.generators.constraint_aware_data_generator import DataGenerationStrategy


class EnhancedTestGenerator(TestGenerator):
    """
    Test generator that combines:
    1. Traditional LLM-based generation (from TestGenerator)
    2. Semantic test generation (from SemanticTestGenerator)
    3. Security mutation testing (from MutationTestGenerator)

    This gives us COMPREHENSIVE coverage:
    - Creative, LLM-generated tests
    - Authoritative, documentation-based tests
    - Security-focused, OWASP Top 10 tests
    """

    def __init__(
        self,
        doc_store,
        flow_store=None,
        semantic_contexts: Optional[Dict[str, DocumentationContext]] = None,
        enable_mutation_testing: bool = True,
        max_mutations_per_pattern: int = 3,
        parameter_constraints: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize Enhanced Test Generator

        Args:
            doc_store: Document store for RAG
            flow_store: Flow store for previous test data
            semantic_contexts: Dict of endpoint semantic contexts
            enable_mutation_testing: Enable security mutation testing
            max_mutations_per_pattern: Max mutations per security pattern
            parameter_constraints: Optional parameter constraints for constraint-aware generation
        """
        super().__init__(doc_store, flow_store, parameter_constraints)

        self.semantic_generator = SemanticTestGenerator()
        self.semantic_contexts = semantic_contexts or {}

        self.enable_mutation_testing = enable_mutation_testing
        if enable_mutation_testing:
            self.mutation_generator = MutationTestGenerator(
                max_tests_per_pattern=max_mutations_per_pattern
            )
            logger.info("🛡️ Security mutation testing enabled")
        else:
            self.mutation_generator = None

        # Initialize combinatorial test generator
        self.combinatorial_generator = CombinatorialTestGenerator(max_combinations=50)
        logger.info("🔢 Combinatorial parameter testing enabled")

        logger.info(
            f"EnhancedTestGenerator initialized "
            f"(semantic_contexts={len(self.semantic_contexts)}, "
            f"mutation_testing={enable_mutation_testing})"
        )

    def generate_comprehensive_tests(
        self,
        endpoint: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive test suite for an endpoint

        Combines:
        1. Semantic tests from documentation (if available)
        2. LLM-generated tests (positive, negative, boundary)
        3. Security mutation tests (OWASP Top 10)

        Args:
            endpoint: Endpoint dict

        Returns:
            List of test cases with metadata
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

        logger.info(f"🧪 Generating comprehensive tests for: {endpoint_key}")

        all_tests = []

        # Part 1: Semantic tests from documentation
        semantic_context = self.semantic_contexts.get(endpoint_key)

        if semantic_context:
            logger.info(f"  📚 Generating semantic tests from documentation...")

            semantic_tests = self.semantic_generator.generate_semantic_tests(
                semantic_context
            )

            # Convert semantic tests to execution format
            for test in semantic_tests:
                execution_test = self._convert_semantic_to_execution(test, endpoint)
                if execution_test:
                    all_tests.append(execution_test)

            logger.info(f"  ✅ Generated {len(semantic_tests)} semantic tests")

        else:
            logger.info(f"  ⚠️  No semantic context available for {endpoint_key}")

        # Part 2: LLM-generated tests
        logger.info(f"  🤖 Generating LLM-based tests...")

        # Generate positive test
        positive_payload = self.generate_test_payload(endpoint, test_type="positive")
        all_tests.append({
            'name': 'LLM: Positive test case',
            'type': 'positive',
            'source': 'llm_generated',
            'payload': positive_payload,
            'expected_status': 200,
            'confidence': 'MEDIUM'
        })

        # Generate negative test
        negative_payload = self.generate_test_payload(endpoint, test_type="negative")
        all_tests.append({
            'name': 'LLM: Negative test case',
            'type': 'negative',
            'source': 'llm_generated',
            'payload': negative_payload,
            'expected_status': 400,
            'confidence': 'MEDIUM'
        })

        # Generate boundary test
        boundary_payload = self.generate_test_payload(endpoint, test_type="boundary")
        all_tests.append({
            'name': 'LLM: Boundary test case',
            'type': 'boundary',
            'source': 'llm_generated',
            'payload': boundary_payload,
            'expected_status': 200,
            'confidence': 'LOW'
        })

        # Part 3: Security mutation tests
        mutation_count = 0
        if self.enable_mutation_testing and self.mutation_generator:
            logger.info(f"  🛡️ Generating security mutation tests...")

            # Use positive payload as base for mutations
            mutation_tests = self.mutation_generator.generate_mutation_tests(
                endpoint,
                base_payload=positive_payload
            )

            all_tests.extend(mutation_tests)
            mutation_count = len(mutation_tests)

            logger.info(f"  ✅ Generated {mutation_count} security mutation tests")

        # Part 4: Combinatorial parameter tests
        combinatorial_count = 0
        if self.combinatorial_generator.should_use_combinatorial_testing(endpoint):
            logger.info(f"  🔢 Generating combinatorial parameter tests...")

            # Get endpoint key for constraints
            endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

            # Define payload generator function for combinatorial testing
            def payload_gen_func(modified_endpoint, param_constraints):
                # Use constraint-aware generation if constraints available
                if endpoint_key in self.parameter_constraints:
                    endpoint_constraints = self.parameter_constraints[endpoint_key]
                    return self.constraint_generator.generate_payload_with_constraints(
                        endpoint=modified_endpoint,
                        parameter_constraints=endpoint_constraints,
                        strategy=DataGenerationStrategy.VALID
                    )
                else:
                    # Fall back to LLM generation
                    return self.generate_test_payload(modified_endpoint, test_type="positive")

            # Generate combinatorial test suite
            combinatorial_tests = self.combinatorial_generator.generate_combinatorial_test_suite(
                endpoint=endpoint,
                base_payload_generator=payload_gen_func,
                parameter_constraints=self.parameter_constraints.get(endpoint_key, {})
            )

            all_tests.extend(combinatorial_tests)
            combinatorial_count = len(combinatorial_tests)

            logger.info(f"  ✅ Generated {combinatorial_count} combinatorial tests")

        logger.info(f"  ✅ Generated 3 LLM-based tests")

        # Summary
        logger.info(
            f"✅ Total tests generated: {len(all_tests)} "
            f"(LLM: 3, mutation: {mutation_count}, combinatorial: {combinatorial_count})"
        )

        return all_tests

    def _convert_semantic_to_execution(
        self,
        semantic_test: Dict[str, Any],
        endpoint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert semantic test to executable format

        Args:
            semantic_test: Test from semantic generator
            endpoint: Endpoint dict

        Returns:
            Executable test dict or None if needs LLM generation
        """
        # If payload is ready, use it
        if semantic_test.get('payload'):
            return {
                'name': semantic_test['name'],
                'type': semantic_test['type'],
                'source': semantic_test['source'],
                'payload': semantic_test['payload'],
                'expected_status': semantic_test.get('expected_status', 200),
                'confidence': semantic_test.get('confidence', 'MEDIUM'),
                'explanation': semantic_test.get('explanation', ''),
                'headers': semantic_test.get('required_headers', {})
            }

        # If needs LLM generation, generate payload
        if semantic_test.get('needs_llm_generation'):
            logger.debug(f"  Generating payload for: {semantic_test['name']}")

            # Use scenario to guide LLM
            scenario = semantic_test.get('scenario', '')

            # Generate payload with scenario context
            payload = self._generate_payload_from_scenario(
                endpoint,
                scenario,
                semantic_test['type']
            )

            return {
                'name': semantic_test['name'],
                'type': semantic_test['type'],
                'source': semantic_test['source'],
                'payload': payload,
                'expected_status': semantic_test.get('expected_status', 200),
                'confidence': semantic_test.get('confidence', 'MEDIUM'),
                'explanation': semantic_test.get('explanation', ''),
                'scenario': scenario
            }

        return None

    def _generate_payload_from_scenario(
        self,
        endpoint: Dict[str, Any],
        scenario: str,
        test_type: str
    ) -> Dict[str, Any]:
        """
        Generate test payload based on a documented scenario

        Args:
            endpoint: Endpoint dict
            scenario: Scenario description from documentation
            test_type: Test type

        Returns:
            Generated payload
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

        # Get documentation context
        doc_context = self._retrieve_documentation_context(endpoint)

        # Build prompt that includes the scenario
        prompt = f"""
Generate a test payload for {endpoint_key} that covers this documented scenario:

Scenario: {scenario}

Endpoint details:
{json.dumps(endpoint, indent=2)}

Documentation context:
{doc_context}

Test type: {test_type}

Requirements:
1. Create a payload that specifically tests the scenario described
2. Use realistic data that matches the scenario
3. Follow best practices from documentation
4. Return ONLY valid JSON payload, no explanations

JSON payload:
"""

        response = self.llm.invoke(prompt)
        payload = self.parse_json_response(response)

        return payload

    def get_test_generation_summary(
        self,
        endpoint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get summary of what tests would be generated for an endpoint

        Args:
            endpoint: Endpoint dict

        Returns:
            Summary dict with semantic, LLM, and mutation test counts
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

        semantic_context = self.semantic_contexts.get(endpoint_key)

        # Get mutation test summary
        mutation_summary = {}
        mutation_count = 0
        if self.enable_mutation_testing and self.mutation_generator:
            mutation_summary = self.mutation_generator.get_mutation_summary(endpoint)
            mutation_count = mutation_summary.get('total_tests', 0)

        if semantic_context:
            semantic_summary = self.semantic_generator.explain_test_generation(
                semantic_context
            )

            return {
                'endpoint': endpoint_key,
                'has_semantic_context': True,
                'semantic_tests': semantic_summary['test_types'],
                'llm_tests': {'positive': 1, 'negative': 1, 'boundary': 1},
                'mutation_tests': mutation_summary.get('by_severity', {}),
                'total_estimated_tests': sum(semantic_summary['test_types'].values()) + 3 + mutation_count,
                'sources': {
                    **semantic_summary['sources_used'],
                    'llm_generated': 3,
                    'mutation_testing': mutation_count
                },
                'security_coverage': {
                    'total_security_tests': mutation_count,
                    'by_severity': mutation_summary.get('by_severity', {}),
                    'by_pattern': mutation_summary.get('by_pattern', {}),
                },
                'coverage_quality': self._calculate_coverage_quality(
                    semantic_summary['sources_used'],
                    mutation_count
                )
            }
        else:
            return {
                'endpoint': endpoint_key,
                'has_semantic_context': False,
                'semantic_tests': {},
                'llm_tests': {'positive': 1, 'negative': 1, 'boundary': 1},
                'mutation_tests': mutation_summary.get('by_severity', {}),
                'total_estimated_tests': 3 + mutation_count,
                'sources': {
                    'llm_generated': 3,
                    'mutation_testing': mutation_count
                },
                'security_coverage': {
                    'total_security_tests': mutation_count,
                    'by_severity': mutation_summary.get('by_severity', {}),
                    'by_pattern': mutation_summary.get('by_pattern', {}),
                },
                'coverage_quality': 'MEDIUM' if mutation_count > 0 else 'BASIC'
            }

    def _calculate_coverage_quality(
        self,
        semantic_sources: Dict[str, int],
        mutation_count: int
    ) -> str:
        """Calculate overall coverage quality rating"""
        semantic_total = sum(semantic_sources.values())

        if semantic_total > 10 and mutation_count > 5:
            return 'EXCELLENT'
        elif semantic_total > 10 or mutation_count > 5:
            return 'HIGH'
        elif semantic_total > 0 or mutation_count > 0:
            return 'MEDIUM'
        else:
            return 'BASIC'

    def prioritize_tests(
        self,
        tests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize tests based on confidence, source, and severity

        Args:
            tests: List of test cases

        Returns:
            Sorted list of tests (highest priority first)
        """
        priority_order = {
            # Documentation-based tests (highest priority)
            'documentation_example': 1,  # Golden! Exact documented usage
            'documented_error': 2,       # Known error scenarios

            # Security tests (high priority for CRITICAL/HIGH severity)
            'mutation_testing': 3,       # OWASP Top 10 security tests

            # Other documentation tests
            'documented_edge_case': 4,   # Known edge cases
            'best_practice': 5,          # Recommended patterns
            'business_rule': 6,          # Business constraints

            # LLM-based tests (lower priority)
            'use_case': 7,               # Scenario tests
            'llm_generated': 8,          # Generic LLM tests
        }

        # Severity order for security tests
        severity_order = {
            'CRITICAL': 0,
            'HIGH': 1,
            'MEDIUM': 2,
            'LOW': 3,
        }

        confidence_order = {
            'HIGH': 0,
            'MEDIUM': 10,
            'LOW': 20,
        }

        def test_priority(test):
            source = test.get('source', 'llm_generated')
            confidence = test.get('confidence', 'MEDIUM')
            severity = test.get('severity', 'LOW')  # For security tests

            source_priority = priority_order.get(source, 99)
            confidence_priority = confidence_order.get(confidence, 15)
            severity_priority = severity_order.get(severity, 10)

            # For security tests, factor in severity
            if source == 'mutation_testing':
                # CRITICAL/HIGH severity security tests get boosted priority
                return (source_priority, severity_priority, confidence_priority)

            # Lower number = higher priority
            return (source_priority, confidence_priority, severity_priority)

        sorted_tests = sorted(tests, key=test_priority)

        logger.info(
            f"Prioritized {len(sorted_tests)} tests "
            f"(golden tests → security → confidence)"
        )

        return sorted_tests
