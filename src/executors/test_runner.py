"""
Test Runner - Executes API tests with intelligent retry
Combines all agents and systems for end-to-end testing
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import httpx
from loguru import logger

from src.config import settings
from src.agents.endpoint_analyzer import EndpointAnalyzer
from src.agents.test_generator import TestGenerator
from src.agents.enhanced_test_generator import EnhancedTestGenerator
from src.agents.error_fixer import ErrorFixer
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore
from src.rl.test_optimizer import TestOptimizer
from src.analysis.change_detector import ChangeDetector
from src.testing.test_healer import TestHealer
from src.workflow.data_flow_tracker import DataFlowTracker
from src.workflow.dependency_graph import DependencyGraph
from src.workflow.state_transition_generator import StateTransitionGenerator
from src.workflow.state_machine_validator import StateMachineValidator
from src.testing.status_code_scenario_generator import StatusCodeScenarioGenerator
from src.testing.status_code_coverage_tracker import StatusCodeCoverageTracker
from src.testing.role_based_scenario_generator import RoleBasedScenarioGenerator, UserRole
from src.testing.role_test_executor import RoleTestExecutor
from src.testing.error_scenario_generator import ErrorScenarioGenerator
from src.testing.error_response_validator import ErrorResponseValidator
from src.validation.schema_validator import SchemaValidator, ValidationResult
from src.validation.openapi_schema_parser import OpenAPISchemaParser
from src.learning.constraint_learner import ConstraintLearner
from src.learning.constraint_updater import ConstraintUpdater


class TestRunner:
    """
    Main test execution engine
    Orchestrates agents, RAG, and HTTP execution for intelligent API testing
    """

    def __init__(
        self,
        base_url: str,
        session_id: str,
        doc_store: DocumentStore,
        max_retries: int = None,
        use_rl: bool = True,
        semantic_contexts: Optional[Dict] = None,
        comprehensive_mode: bool = False,
        parameter_constraints: Optional[Dict] = None
    ):
        """
        Initialize Test Runner

        Args:
            base_url: API base URL
            session_id: Unique session ID for this test run
            doc_store: Document store for RAG
            max_retries: Max retry attempts (default from settings)
            use_rl: Use RL-based test prioritization (default True)
            semantic_contexts: Optional semantic contexts from documentation analysis
            comprehensive_mode: Generate comprehensive test suite (semantic + LLM + mutation tests)
            parameter_constraints: Optional parameter constraints for test data generation
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id
        self.doc_store = doc_store
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.use_rl = use_rl
        self.semantic_contexts = semantic_contexts
        self.comprehensive_mode = comprehensive_mode
        self.parameter_constraints = parameter_constraints or {}

        # Initialize Flow Store for this session
        self.flow_store = FlowStore(session_id=session_id)

        # Initialize agents
        self.analyzer = EndpointAnalyzer()

        # Use EnhancedTestGenerator if semantic contexts available or comprehensive mode enabled
        if semantic_contexts or comprehensive_mode:
            self.generator = EnhancedTestGenerator(
                doc_store,
                self.flow_store,
                semantic_contexts=semantic_contexts,
                enable_mutation_testing=True,
                max_mutations_per_pattern=3,
                parameter_constraints=self.parameter_constraints
            )
            mode = "comprehensive" if comprehensive_mode else "semantic"
            logger.info(f"🧠 Using EnhancedTestGenerator ({mode} mode) for {len(semantic_contexts or {})} endpoints")
        else:
            self.generator = TestGenerator(
                doc_store,
                self.flow_store,
                parameter_constraints=self.parameter_constraints
            )
            logger.info("Using standard TestGenerator")

        # Log constraint availability
        if self.parameter_constraints:
            total_endpoints = len(self.parameter_constraints)
            total_params_with_constraints = sum(
                sum(1 for p in params.values() if p.get('constraints'))
                for params in self.parameter_constraints.values()
            )
            logger.info(f"🔍 Parameter constraints loaded for {total_endpoints} endpoints ({total_params_with_constraints} params with constraints)")

        self.fixer = ErrorFixer(doc_store, self.flow_store)

        # Initialize RL optimizer
        if use_rl:
            self.rl_optimizer = TestOptimizer()
            logger.info("🧠 RL Test Optimizer enabled")
        else:
            self.rl_optimizer = None
            logger.info("Traditional test ordering enabled")

        # Initialize self-healing components
        self.change_detector = ChangeDetector()
        self.test_healer = TestHealer(auto_heal=True, require_confirmation=False)
        self.healing_history = []
        logger.info("🔄 Self-Healing Tests enabled")

        # Initialize data flow tracker for workflow intelligence
        self.data_flow_tracker = DataFlowTracker()
        logger.info("💉 Data Flow Tracker enabled (ID extraction & injection)")

        # Test results
        self.results = []

        # Endpoint metadata tracking for RL
        self.endpoint_metadata = {}

        # Expected responses tracking (for change detection)
        self.expected_responses = {}

        # HTTP client (will be created in async context)
        self.client = None

        logger.info(f"TestRunner initialized for session: {session_id}")

    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=settings.HTTP_MAX_CONNECTIONS),
            follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    async def test_endpoint(
        self,
        endpoint: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test a single endpoint with intelligent retry

        Args:
            endpoint: Endpoint dict from analyzer
            headers: Optional custom headers

        Returns:
            Test result dict
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🧪 Testing: {endpoint_key}")
        logger.info(f"{'=' * 80}")

        # Generate initial test payload
        logger.info("🤖 Generating test payload with AI...")
        test_payload = self.generator.generate_test_payload(endpoint, test_type="positive")

        # Prepare headers
        test_headers = {"Content-Type": "application/json"}
        if headers:
            test_headers.update(headers)

        # Add authentication if needed
        if endpoint.get('auth_required'):
            token = await self._get_auth_token()
            if token:
                test_headers['Authorization'] = f"Bearer {token}"
                logger.info("🔑 Added authentication token")

        # Try testing with retries
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"\n🚀 Attempt {attempt}/{self.max_retries}")

            result = await self._execute_request(
                endpoint, test_payload, test_headers, attempt
            )

            # If successful, return
            if result['success']:
                logger.info(f"✅ SUCCESS on attempt {attempt}")

                # Set baseline expected response on first successful test
                if endpoint_key not in self.expected_responses:
                    self.set_expected_response(
                        endpoint_key,
                        result['status_code'],
                        result['response']
                    )
                    logger.debug(f"📝 Set baseline response for {endpoint_key}")

                return result

            # If last attempt, return failure
            if attempt == self.max_retries:
                logger.warning(f"❌ FAILED after {self.max_retries} attempts")
                return result

            # Try to fix the error
            logger.info(f"🔧 Analyzing error and generating fix...")

            # Check if should retry
            if not self.fixer.should_retry(result['status_code'], result['response']):
                logger.info("⏭️  Error not retriable, skipping remaining attempts")
                return result

            # Generate fix
            test_payload = self.fixer.fix_failed_test(
                endpoint,
                test_payload,
                result['response'],
                result['status_code']
            )

            logger.info(f"✨ Generated fix, retrying...")

            # Small delay before retry
            await asyncio.sleep(settings.RETRY_DELAY_SECONDS)

        return result  # Should never reach here, but just in case

    async def test_endpoint_comprehensive(
        self,
        endpoint: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Test endpoint with comprehensive test suite (semantic + LLM + mutation tests)

        Args:
            endpoint: Endpoint dict from analyzer
            headers: Optional custom headers

        Returns:
            List of test results
        """
        if not hasattr(self.generator, 'generate_comprehensive_tests'):
            logger.warning("Generator doesn't support comprehensive mode, falling back to single test")
            result = await self.test_endpoint(endpoint, headers)
            return [result]

        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🧪 Comprehensive Testing: {endpoint_key}")
        logger.info(f"{'=' * 80}")

        # Generate comprehensive test suite
        logger.info("🤖 Generating comprehensive test suite...")
        all_tests = self.generator.generate_comprehensive_tests(endpoint)

        logger.info(f"✅ Generated {len(all_tests)} tests")

        # Prioritize tests
        prioritized_tests = self.generator.prioritize_tests(all_tests)

        # Prepare headers
        test_headers = {"Content-Type": "application/json"}
        if headers:
            test_headers.update(headers)

        # Add authentication if needed
        if endpoint.get('auth_required'):
            token = await self._get_auth_token()
            if token:
                test_headers['Authorization'] = f"Bearer {token}"
                logger.info("🔑 Added authentication token")

        # Execute each test
        results = []
        for idx, test in enumerate(prioritized_tests, 1):
            test_name = test.get('name', f'Test {idx}')
            test_source = test.get('source', 'unknown')
            test_confidence = test.get('confidence', 'MEDIUM')

            logger.info(f"\n🧪 Test {idx}/{len(prioritized_tests)}: {test_name}")
            logger.info(f"   Source: {test_source} | Confidence: {test_confidence}")

            payload = test.get('payload', {})

            # Execute with single attempt (no retries for comprehensive mode)
            result = await self._execute_request(
                endpoint, payload, test_headers, attempt=1
            )

            # Add test metadata to result
            result['test_name'] = test_name
            result['test_source'] = test_source
            result['test_type'] = test.get('type', 'unknown')
            result['test_confidence'] = test_confidence
            result['test_severity'] = test.get('severity')
            result['test_pattern'] = test.get('pattern')

            results.append(result)

            # Small delay between tests
            await asyncio.sleep(0.2)

        # Summary
        passed = sum(1 for r in results if r.get('success'))
        logger.info(f"\n✅ Comprehensive tests: {passed}/{len(results)} passed")

        return results

    async def _execute_request(
        self,
        endpoint: Dict[str, Any],
        payload: Dict[str, Any],
        headers: Dict[str, str],
        attempt: int
    ) -> Dict[str, Any]:
        """
        Execute the actual HTTP request

        Args:
            endpoint: Endpoint dict
            payload: Request payload
            headers: Request headers
            attempt: Attempt number

        Returns:
            Result dict with success, status_code, response, etc.
        """
        # Extract resource name from path for data flow tracking
        path = endpoint.get('path', '')
        path_parts = [p for p in path.split('/') if p and not p.startswith('{')]
        resource_hint = path_parts[-1] if path_parts else None

        # Inject extracted values into path and payload
        injected_path = self.data_flow_tracker.inject_into_path(path, resource_hint)
        injected_payload = self.data_flow_tracker.inject_into_body(payload, resource_hint) if payload else payload

        # Log injections if any occurred
        if injected_path != path:
            logger.debug(f"   💉 Injected values into path: {path} → {injected_path}")
        if injected_payload != payload:
            logger.debug(f"   💉 Injected values into payload")

        endpoint_key = f"{endpoint.get('method', 'GET')} {injected_path}"
        method = endpoint.get('method', 'GET').upper()
        url = f"{self.base_url}{injected_path}"

        logger.info(f"   URL: {url}")
        logger.info(f"   Method: {method}")

        # Store request in Flow DB (with injected payload)
        self.flow_store.store_request(endpoint_key, injected_payload, {"attempt": attempt})

        start_time = time.time()

        try:
            # Execute request based on method
            if method == 'GET':
                # Add payload as query params for GET
                if injected_payload:
                    query_string = urlencode(injected_payload)
                    url = f"{url}?{query_string}"
                response = await self.client.get(url, headers=headers)

            elif method == 'POST':
                logger.info(f"   Payload: {str(injected_payload)[:200]}...")
                response = await self.client.post(url, headers=headers, json=injected_payload)

            elif method == 'PUT':
                logger.info(f"   Payload: {str(injected_payload)[:200]}...")
                response = await self.client.put(url, headers=headers, json=injected_payload)

            elif method == 'PATCH':
                logger.info(f"   Payload: {str(injected_payload)[:200]}...")
                response = await self.client.patch(url, headers=headers, json=injected_payload)

            elif method == 'DELETE':
                response = await self.client.delete(url, headers=headers)

            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            elapsed_time = time.time() - start_time

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_text": response.text[:500]}

            success = 200 <= response.status_code < 300

            # Log result
            if success:
                logger.info(f"   ✅ Status: {response.status_code}")
                logger.info(f"   ⏱️  Time: {elapsed_time:.2f}s")
                logger.info(f"   📥 Response: {str(response_data)[:200]}...")
            else:
                logger.warning(f"   ❌ Status: {response.status_code}")
                logger.warning(f"   ⏱️  Time: {elapsed_time:.2f}s")
                logger.warning(f"   📥 Error: {str(response_data)[:200]}...")

            # Store response in Flow DB
            self.flow_store.store_response(
                endpoint_key,
                response_data,
                response.status_code,
                success,
                {"attempt": attempt, "elapsed_time": elapsed_time}
            )

            # Build result
            result = {
                'endpoint': endpoint_key,
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'success': success,
                'attempts': attempt,
                'elapsed_time': elapsed_time,
                'final_payload': injected_payload,  # Use injected payload
                'response': response_data,
                'headers': headers,
            }

            # Self-Healing: Detect API changes and auto-heal tests
            if endpoint_key in self.expected_responses:
                expected = self.expected_responses[endpoint_key]
                actual = {
                    'status_code': response.status_code,
                    'body': response_data
                }

                # Detect changes
                changes = self.change_detector.detect_changes(expected, actual)

                if changes:
                    logger.info(f"🔄 Detected {len(changes)} API changes")

                    # Build test spec for healing
                    test_spec = {
                        'name': f'Test for {endpoint_key}',
                        'endpoint': endpoint_key,
                        'expected_status': expected.get('status_code', 200),
                        'expected_response': expected.get('body', {})
                    }

                    # Try to heal the test
                    healed_test = self.test_healer.heal_test(test_spec, actual, changes)

                    # Update expected response with healed version
                    self.expected_responses[endpoint_key] = {
                        'status_code': healed_test.get('expected_status'),
                        'body': healed_test.get('expected_response')
                    }

                    # Track healing action
                    healing_record = {
                        'endpoint': endpoint_key,
                        'timestamp': datetime.now().isoformat(),
                        'changes_detected': len(changes),
                        'changes': [
                            {
                                'type': c.change_type,
                                'field': c.field_path,
                                'severity': c.severity,
                                'description': c.description
                            }
                            for c in changes
                        ],
                        'healed': True,
                        'auto_heal': True
                    }
                    self.healing_history.append(healing_record)

                    # Add healing info to result
                    result['self_healing'] = {
                        'changes_detected': len(changes),
                        'auto_healed': True,
                        'healing_actions': len(self.healing_history)
                    }

                    logger.info(f"✅ Test auto-healed (total healing actions: {len(self.healing_history)})")

            # Extract IDs and values from successful responses for data flow tracking
            if success and isinstance(response_data, dict):
                extracted_values = self.data_flow_tracker.extract_from_response(
                    endpoint_key=endpoint_key,
                    response_body=response_data,
                    status_code=response.status_code
                )
                if extracted_values:
                    logger.info(f"   💉 Extracted {len(extracted_values)} values for data flow")
                    result['extracted_values'] = [
                        {
                            'field': ev.field_name,
                            'value': str(ev.value)[:50]  # Truncate for display
                        }
                        for ev in extracted_values
                    ]

            return result

        except Exception as e:
            elapsed_time = time.time() - start_time

            logger.error(f"   ❌ Exception: {str(e)}")

            return {
                'endpoint': endpoint_key,
                'url': url,
                'method': method,
                'status_code': 0,
                'success': False,
                'attempts': attempt,
                'elapsed_time': elapsed_time,
                'final_payload': payload,
                'response': {'error': str(e)},
                'error': str(e),
            }

    async def _get_auth_token(self) -> Optional[str]:
        """
        Get authentication token from previous successful login

        Returns:
            Token string if found, None otherwise
        """
        # Query Flow DB for token
        context = self.flow_store.query_for_context(
            "authentication token bearer from successful login",
            n_results=1
        )

        if not context or context == "No previous flow data found.":
            return None

        # Try to extract token using regex
        import re

        # Common token patterns
        patterns = [
            r'"token":\s*"([^"]+)"',
            r'"access_token":\s*"([^"]+)"',
            r'"bearer":\s*"([^"]+)"',
            r'Bearer\s+([A-Za-z0-9._-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, context)
            if match:
                token = match.group(1)
                logger.debug(f"Found token: {token[:20]}...")
                return token

        return None

    def _build_test_context(self) -> Dict[str, Any]:
        """
        Build context for RL state representation

        Returns:
            Context dict with current test environment state
        """
        return {
            'time': datetime.now(),
            'session_id': self.session_id,
            'dependency_health': 100,  # Default to healthy, can be enhanced
        }

    def _enrich_endpoint_metadata(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich endpoint with metadata for RL

        Args:
            endpoint: Endpoint dict

        Returns:
            Endpoint dict with added metadata
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

        # Get or create metadata
        if endpoint_key not in self.endpoint_metadata:
            self.endpoint_metadata[endpoint_key] = {
                'total_tests': 0,
                'failures': 0,
                'last_test_time': None,
                'last_failure_time': None,
            }

        metadata = self.endpoint_metadata[endpoint_key]

        # Calculate failure rate
        failure_rate = 0
        if metadata['total_tests'] > 0:
            failure_rate = (metadata['failures'] / metadata['total_tests']) * 100

        # Calculate days since change (placeholder - can be enhanced with git integration)
        days_since_change = 30  # Default to "stable"

        # Add enriched data to endpoint
        enriched = {
            **endpoint,
            'failure_rate': failure_rate,
            'days_since_change': days_since_change,
            'total_tests': metadata['total_tests'],
        }

        return enriched

    def _update_endpoint_metadata(self, endpoint_key: str, success: bool):
        """
        Update endpoint metadata after test

        Args:
            endpoint_key: Endpoint identifier
            success: Whether test passed
        """
        if endpoint_key not in self.endpoint_metadata:
            self.endpoint_metadata[endpoint_key] = {
                'total_tests': 0,
                'failures': 0,
                'last_test_time': None,
                'last_failure_time': None,
            }

        metadata = self.endpoint_metadata[endpoint_key]
        metadata['total_tests'] += 1
        metadata['last_test_time'] = datetime.now()

        if not success:
            metadata['failures'] += 1
            metadata['last_failure_time'] = datetime.now()

    async def test_all_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        ordered: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Test all endpoints with RL-based prioritization

        Args:
            endpoints: List of endpoint dicts
            ordered: Use optimal testing order (default True)

        Returns:
            List of test results
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🚀 Starting Test Session: {self.session_id}")
        logger.info(f"📊 Total Endpoints: {len(endpoints)}")
        logger.info(f"{'=' * 80}")

        # Enrich endpoints with metadata for RL
        enriched_endpoints = [
            self._enrich_endpoint_metadata(ep) for ep in endpoints
        ]

        # Determine testing order
        if ordered and self.use_rl and self.rl_optimizer:
            logger.info("🧠 Using RL-based test prioritization")

            # Build context for RL state
            context = self._build_test_context()

            # Let RL prioritize endpoints
            ordered_endpoints = self.rl_optimizer.prioritize_endpoints(
                enriched_endpoints,
                context
            )

        elif ordered:
            # Fallback to traditional analyzer ordering
            logger.info("Using traditional analyzer ordering")
            endpoint_order = self.analyzer.get_testing_order(enriched_endpoints)

            endpoint_map = {
                f"{ep.get('method')} {ep.get('path')}": ep
                for ep in enriched_endpoints
            }
            ordered_endpoints = [
                endpoint_map[key]
                for key in endpoint_order
                if key in endpoint_map
            ]
        else:
            ordered_endpoints = enriched_endpoints

        # Test each endpoint
        self.results = []

        for idx, endpoint in enumerate(ordered_endpoints, 1):
            rl_priority = endpoint.get('rl_priority', 'normal')

            # Skip if RL says to skip
            if rl_priority == 'skip':
                logger.info(
                    f"\n📍 Progress: {idx}/{len(ordered_endpoints)} "
                    f"⏭️  SKIPPING (RL confidence: high stability)"
                )

                # Still probe to validate RL decision (lightweight check)
                skipped_result = await self._probe_endpoint(endpoint)
                skipped_result['skipped'] = True
                skipped_result['rl_priority'] = rl_priority
                skipped_result['rl_state'] = endpoint.get('rl_state')

                self.results.append(skipped_result)

            else:
                priority_icon = {
                    'critical': '🔴',
                    'high': '🟠',
                    'normal': '🟡',
                    'low': '🟢',
                }[rl_priority]

                logger.info(
                    f"\n📍 Progress: {idx}/{len(ordered_endpoints)} "
                    f"{priority_icon} Priority: {rl_priority.upper()}"
                )

                # Use comprehensive mode if enabled
                if self.comprehensive_mode:
                    endpoint_results = await self.test_endpoint_comprehensive(endpoint)

                    # Add RL metadata to all results
                    for result in endpoint_results:
                        result['rl_priority'] = rl_priority
                        result['rl_state'] = endpoint.get('rl_state')
                        self.results.append(result)

                    # Update endpoint metadata based on any failures
                    endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
                    any_success = any(r.get('success', False) for r in endpoint_results)
                    self._update_endpoint_metadata(endpoint_key, any_success)

                else:
                    result = await self.test_endpoint(endpoint)

                    # Add RL metadata to result
                    result['rl_priority'] = rl_priority
                    result['rl_state'] = endpoint.get('rl_state')

                    self.results.append(result)

                    # Update endpoint metadata
                    endpoint_key = result.get('endpoint', '')
                    self._update_endpoint_metadata(endpoint_key, result.get('success', False))

            # Small delay between tests
            await asyncio.sleep(0.5)

        # RL Learning: Update Q-values based on results
        if self.use_rl and self.rl_optimizer:
            logger.info("\n🎓 RL Learning from results...")
            self.rl_optimizer.learn_from_results(self.results)

            # Show RL metrics
            metrics = self.rl_optimizer.get_metrics()
            logger.info(f"📊 RL Metrics:")
            logger.info(f"   Time saved: {metrics['time_saved']:.1f}s")
            logger.info(f"   Failures caught: {metrics['failures_caught']}")
            logger.info(f"   Failures missed: {metrics['failures_missed']}")
            logger.info(f"   Correct skips: {metrics['correct_skips']}")
            logger.info(f"   Avg reward: {metrics['avg_reward_per_episode']:+.2f}")

        # Print summary
        self._print_summary()

        return self.results

    async def test_state_transitions(
        self,
        endpoints: List[Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test state transitions (CREATE → READ → UPDATE → DELETE workflows)

        Args:
            endpoints: List of endpoint dicts
            headers: Optional custom headers

        Returns:
            State transition test results
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🔄 STATE TRANSITION TESTING")
        logger.info(f"{'=' * 80}")

        # Step 1: Build dependency graph
        logger.info("📊 Building dependency graph...")
        dep_graph = DependencyGraph()
        dep_graph.build_graph(endpoints)

        graph_summary = dep_graph.get_graph_summary()
        logger.info(f"   Resources: {graph_summary['total_resources']}")
        logger.info(f"   Dependencies: {graph_summary['total_dependencies']}")
        logger.info(f"   CRUD Resources: {graph_summary['crud_resource_count']}")

        # Step 2: Generate state transition sequences
        logger.info("\n🔄 Generating state transition test sequences...")
        sequence_generator = StateTransitionGenerator(dep_graph)
        sequences = sequence_generator.generate_all_sequences()

        sequence_summary = sequence_generator.get_summary()
        logger.info(f"   Total sequences: {sequence_summary['total_sequences']}")
        logger.info(f"   Total transitions: {sequence_summary['total_transitions']}")
        logger.info(f"   Sequences by type:")
        for seq_type, count in sequence_summary['sequences_by_type'].items():
            logger.info(f"      {seq_type}: {count}")

        # Step 3: Execute state transition sequences
        logger.info("\n🧪 Executing state transition sequences...")
        validator = StateMachineValidator(
            base_url=self.base_url,
            headers=headers or {},
            timeout=settings.HTTP_TIMEOUT_SECONDS
        )

        sequence_results = await validator.validate_multiple_sequences(
            sequences,
            test_data_generator=self.generator
        )

        # Step 4: Generate validation report
        validation_report = validator.get_validation_report(sequence_results)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"STATE TRANSITION TESTING COMPLETE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total Sequences: {validation_report['summary']['total_sequences']}")
        logger.info(f"Successful: {validation_report['summary']['successful_sequences']} ✅")
        logger.info(f"Failed: {validation_report['summary']['failed_sequences']} ❌")
        logger.info(f"Success Rate: {validation_report['summary']['success_rate']:.1f}%")
        logger.info(f"Avg Time: {validation_report['summary']['avg_sequence_time_ms']:.0f}ms")

        if validation_report['failed_sequences']:
            logger.warning(f"\nFailed Sequences:")
            for failed in validation_report['failed_sequences']:
                logger.warning(f"  - {failed['description']}: {failed['failure_reason']}")

        return {
            'dependency_graph': graph_summary,
            'sequence_summary': sequence_summary,
            'validation_report': validation_report,
            'sequence_results': sequence_results
        }

    async def test_all_with_state_transitions(
        self,
        endpoints: List[Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
        run_state_transitions: bool = True
    ) -> Dict[str, Any]:
        """
        Run complete test suite including individual endpoint tests + state transitions

        Args:
            endpoints: List of endpoint dicts
            headers: Optional custom headers
            run_state_transitions: Include state transition testing (default True)

        Returns:
            Combined test results
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🚀 COMPREHENSIVE TEST SUITE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Endpoints: {len(endpoints)}")
        logger.info(f"Comprehensive Mode: {self.comprehensive_mode}")
        logger.info(f"State Transitions: {run_state_transitions}")
        logger.info(f"RL Enabled: {self.use_rl}")
        logger.info(f"{'=' * 80}\n")

        # Phase 1: Individual endpoint testing
        logger.info("📍 Phase 1: Individual Endpoint Testing")
        endpoint_results = await self.test_all_endpoints(endpoints, ordered=True)

        # Phase 2: State transition testing
        state_transition_results = None
        if run_state_transitions:
            logger.info("\n📍 Phase 2: State Transition Testing")
            state_transition_results = await self.test_state_transitions(
                endpoints,
                headers=headers
            )

        # Combined summary
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🎉 COMPREHENSIVE TEST SUITE COMPLETE")
        logger.info(f"{'=' * 80}")

        total_endpoint_tests = len(endpoint_results)
        passed_endpoint_tests = sum(1 for r in endpoint_results if r.get('success'))

        logger.info(f"Endpoint Tests:")
        logger.info(f"   Total: {total_endpoint_tests}")
        logger.info(f"   Passed: {passed_endpoint_tests}")
        logger.info(f"   Failed: {total_endpoint_tests - passed_endpoint_tests}")

        if state_transition_results:
            st_summary = state_transition_results['validation_report']['summary']
            logger.info(f"\nState Transition Tests:")
            logger.info(f"   Total Sequences: {st_summary['total_sequences']}")
            logger.info(f"   Passed: {st_summary['successful_sequences']}")
            logger.info(f"   Failed: {st_summary['failed_sequences']}")
            logger.info(f"   Total Transitions: {st_summary['total_transitions']}")

        logger.info(f"{'=' * 80}\n")

        return {
            'endpoint_results': endpoint_results,
            'state_transition_results': state_transition_results,
            'summary': {
                'total_endpoint_tests': total_endpoint_tests,
                'passed_endpoint_tests': passed_endpoint_tests,
                'failed_endpoint_tests': total_endpoint_tests - passed_endpoint_tests,
                'endpoint_success_rate': (passed_endpoint_tests / total_endpoint_tests * 100) if total_endpoint_tests > 0 else 0,
                'state_transition_enabled': run_state_transitions,
                'state_transition_summary': state_transition_results['validation_report']['summary'] if state_transition_results else None
            }
        }

    async def _probe_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lightweight probe to check if skipped endpoint would have failed
        Used for RL validation without full test execution

        Args:
            endpoint: Endpoint to probe

        Returns:
            Probe result dict
        """
        method = endpoint.get('method', 'GET').upper()
        url = f"{self.base_url}{endpoint.get('path', '')}"
        endpoint_key = f"{method} {endpoint.get('path', '')}"

        start_time = time.time()

        try:
            # Quick HEAD or GET request (no payload)
            if method in ['GET', 'HEAD']:
                response = await self.client.request(method, url, timeout=5.0)
            else:
                # For POST/PUT/PATCH, just check if endpoint exists
                response = await self.client.head(url, timeout=5.0)

            elapsed_time = time.time() - start_time
            success = 200 <= response.status_code < 300

            return {
                'endpoint': endpoint_key,
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'success': success,
                'would_have_failed': not success,
                'elapsed_time': elapsed_time,
                'attempts': 0,  # No retries for probes
                'final_payload': {},
                'response': {},
                'estimated_time': 5.0,  # Estimated time saved
            }

        except Exception as e:
            elapsed_time = time.time() - start_time

            return {
                'endpoint': endpoint_key,
                'url': url,
                'method': method,
                'status_code': 0,
                'success': False,
                'would_have_failed': True,
                'elapsed_time': elapsed_time,
                'attempts': 0,
                'final_payload': {},
                'response': {},
                'error': str(e),
                'estimated_time': 5.0,
            }

    def _print_summary(self):
        """Print test session summary"""
        if not self.results:
            return

        passed = sum(1 for r in self.results if r.get('success'))
        failed = len(self.results) - passed

        logger.info(f"\n{'=' * 80}")
        logger.info(f"📊 TEST SESSION SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total Tests: {len(self.results)}")
        logger.info(f"✅ Passed: {passed} ({passed/len(self.results)*100:.1f}%)")
        logger.info(f"❌ Failed: {failed} ({failed/len(self.results)*100:.1f}%)")

        # Calculate stats
        if self.results:
            total_time = sum(r.get('elapsed_time', 0) for r in self.results)
            avg_time = total_time / len(self.results)
            total_attempts = sum(r.get('attempts', 1) for r in self.results)

            logger.info(f"⏱️  Total Time: {total_time:.2f}s")
            logger.info(f"⏱️  Avg Time: {avg_time:.2f}s")
            logger.info(f"🔄 Total Attempts: {total_attempts}")

        # Flow DB stats
        flow_stats = self.flow_store.get_stats()
        logger.info(f"\n💾 Flow DB Stats:")
        logger.info(f"   Requests Stored: {flow_stats['requests']}")
        logger.info(f"   Responses Stored: {flow_stats['responses']}")
        logger.info(f"   Successful: {flow_stats['successful_responses']}")

        logger.info(f"{'=' * 80}\n")

    def set_expected_response(self, endpoint_key: str, status_code: int, body: Dict[str, Any]):
        """
        Set expected response for an endpoint (for change detection)

        Args:
            endpoint_key: Endpoint identifier (e.g., "POST /api/users")
            status_code: Expected status code
            body: Expected response body
        """
        self.expected_responses[endpoint_key] = {
            'status_code': status_code,
            'body': body
        }

    def get_healing_report(self) -> Dict[str, Any]:
        """
        Get self-healing report

        Returns:
            Report dict with healing statistics and history
        """
        if not self.healing_history:
            return {
                'total_healing_actions': 0,
                'endpoints_healed': 0,
                'history': [],
                'healer_stats': self.test_healer.get_healing_report()
            }

        endpoints_healed = len(set(h['endpoint'] for h in self.healing_history))
        total_changes = sum(h['changes_detected'] for h in self.healing_history)

        # Categorize changes by severity
        severity_counts = {'BREAKING': 0, 'NON_BREAKING': 0, 'MINOR': 0}
        for record in self.healing_history:
            for change in record.get('changes', []):
                severity = change.get('severity', 'UNKNOWN')
                if severity in severity_counts:
                    severity_counts[severity] += 1

        return {
            'total_healing_actions': len(self.healing_history),
            'endpoints_healed': endpoints_healed,
            'total_changes_detected': total_changes,
            'severity_breakdown': severity_counts,
            'history': self.healing_history,
            'healer_stats': self.test_healer.get_healing_report()
        }

    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get structured summary of test results

        Returns:
            Summary dict
        """
        if not self.results:
            return {"error": "No tests run yet"}

        passed = sum(1 for r in self.results if r.get('success'))
        failed = len(self.results) - passed

        return {
            "session_id": self.session_id,
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(self.results) * 100 if self.results else 0,
            "total_time": sum(r.get('elapsed_time', 0) for r in self.results),
            "avg_time": sum(r.get('elapsed_time', 0) for r in self.results) / len(self.results),
            "total_attempts": sum(r.get('attempts', 1) for r in self.results),
            "flow_stats": self.flow_store.get_stats(),
            "healing_report": self.get_healing_report(),
            "results": self.results,
        }

    async def test_status_code_coverage(
        self,
        endpoints: List[Dict[str, Any]],
        documented_responses: Optional[Dict[str, List[int]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test status code coverage - ensure all documented error scenarios are tested

        Args:
            endpoints: List of endpoint dicts
            documented_responses: Optional dict mapping endpoint_key to list of documented status codes
            headers: Optional custom headers

        Returns:
            Status code coverage report
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📊 STATUS CODE COVERAGE TESTING")
        logger.info(f"{'=' * 80}")

        # Step 1: Generate status code scenarios
        logger.info("🔧 Generating status code test scenarios...")
        scenario_generator = StatusCodeScenarioGenerator(documented_responses)

        scenarios = scenario_generator.generate_all_scenarios(
            endpoints,
            documented_responses
        )

        scenario_summary = scenario_generator.get_summary(scenarios)
        logger.info(f"   Total scenarios: {scenario_summary['total_scenarios']}")
        logger.info(f"   Unique status codes: {scenario_summary['unique_status_codes']}")
        logger.info(f"   Scenario types:")
        for stype, count in scenario_summary['by_type'].items():
            logger.info(f"      {stype}: {count}")

        # Step 2: Initialize coverage tracker
        logger.info("\n🧪 Executing status code scenarios...")
        coverage_tracker = StatusCodeCoverageTracker(
            base_url=self.base_url,
            default_headers=headers or {},
            timeout=settings.HTTP_TIMEOUT_SECONDS
        )

        # Set documented codes for tracking
        if documented_responses:
            for endpoint_key, codes in documented_responses.items():
                coverage_tracker.set_documented_codes(endpoint_key, codes)

        # Step 3: Execute all scenarios
        test_results = await coverage_tracker.execute_all_scenarios(scenarios)

        # Step 4: Generate coverage report
        logger.info("\n📊 Calculating coverage...")
        coverage_stats = coverage_tracker.get_overall_coverage()
        coverage_report_text = coverage_tracker.generate_coverage_report()

        logger.info(f"\n{coverage_report_text}")

        # Summary
        logger.info(f"\n{'=' * 80}")
        logger.info(f"STATUS CODE COVERAGE COMPLETE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Overall Coverage: {coverage_stats['overall_coverage_percentage']:.1f}%")
        logger.info(f"Total Tests: {coverage_stats['total_tests']}")
        logger.info(f"Match Rate: {coverage_stats['match_rate']:.1f}%")

        failed = coverage_tracker.get_failed_scenarios()
        if failed:
            logger.warning(f"\n⚠️  {len(failed)} scenarios didn't return expected status code:")
            for result in failed[:10]:  # Show first 10
                logger.warning(
                    f"   {result.scenario.endpoint_key}: "
                    f"Expected {result.expected_status_code}, got {result.actual_status_code}"
                )

        return {
            'scenario_summary': scenario_summary,
            'coverage_stats': coverage_stats,
            'coverage_report': coverage_report_text,
            'test_results': [
                {
                    'endpoint': r.scenario.endpoint_key,
                    'expected_code': r.expected_status_code,
                    'actual_code': r.actual_status_code,
                    'matched': r.matched,
                    'scenario_type': r.scenario.scenario_type,
                    'description': r.scenario.description
                }
                for r in test_results
            ]
        }

    async def test_role_based_access_control(
        self,
        endpoints: List[Dict[str, Any]],
        roles: Optional[List[UserRole]] = None,
        auth_tokens: Optional[Dict[UserRole, str]] = None,
        custom_permissions: Optional[Dict[str, Dict[UserRole, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Test role-based access control (RBAC) across all endpoints

        Args:
            endpoints: List of endpoint dicts
            roles: List of roles to test (defaults to all: admin, user, guest, unauthenticated)
            auth_tokens: Authentication tokens for each role
            custom_permissions: Custom permission matrix overrides
            headers: Optional default headers

        Returns:
            RBAC test results and security report
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🔐 ROLE-BASED ACCESS CONTROL (RBAC) TESTING")
        logger.info(f"{'=' * 80}")

        # Step 1: Generate role-based test scenarios
        logger.info("🔧 Generating role-based test scenarios...")
        scenario_generator = RoleBasedScenarioGenerator(
            custom_permissions=custom_permissions,
            auth_tokens=auth_tokens or {}
        )

        scenarios = scenario_generator.generate_all_role_scenarios(
            endpoints,
            roles=roles
        )

        scenario_summary = scenario_generator.get_summary(scenarios)
        logger.info(f"   Total scenarios: {scenario_summary['total_scenarios']}")
        logger.info(f"   Roles tested: {scenario_summary['unique_roles']}")
        logger.info(f"   Scenarios by role:")
        for role, count in scenario_summary['by_role'].items():
            logger.info(f"      {role}: {count}")

        # Step 2: Show permission matrix
        logger.info("\n📊 Permission Matrix:")
        permission_matrix = scenario_generator.visualize_permission_matrix(
            endpoints,
            roles=roles
        )
        logger.info(f"\n{permission_matrix}")

        # Step 3: Execute role-based tests
        logger.info("\n🧪 Executing role-based tests...")
        role_executor = RoleTestExecutor(
            base_url=self.base_url,
            default_headers=headers or {},
            timeout=settings.HTTP_TIMEOUT_SECONDS
        )

        test_results = await role_executor.execute_all_scenarios(scenarios)

        # Step 4: Generate security report
        logger.info("\n🔒 Generating security report...")
        security_report = role_executor.generate_security_report()
        role_summary = role_executor.get_role_summary()

        logger.info(f"\n{security_report}")

        # Summary
        logger.info(f"\n{'=' * 80}")
        logger.info(f"RBAC TESTING COMPLETE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total Tests: {role_summary['total_tests']}")
        logger.info(f"Correctness Rate: {role_summary['correctness_rate']:.1f}%")
        logger.info(f"Violations: {role_summary['total_violations']}")

        if role_summary['total_violations'] > 0:
            logger.warning(f"\n⚠️  Permission violations detected:")
            logger.warning(f"   Critical: {role_summary['violations_by_severity']['critical']}")
            logger.warning(f"   Medium: {role_summary['violations_by_severity']['medium']}")
            logger.warning(f"   Low: {role_summary['violations_by_severity']['low']}")
        else:
            logger.success(f"\n✅ No permission violations detected!")

        return {
            'scenario_summary': scenario_summary,
            'role_summary': role_summary,
            'security_report': security_report,
            'permission_matrix': permission_matrix,
            'violations': [
                {
                    'endpoint': v.endpoint_key,
                    'role': v.role.value,
                    'violation_type': v.violation_type,
                    'severity': v.severity,
                    'description': v.description
                }
                for v in role_executor.violations
            ],
            'test_results': [
                {
                    'endpoint': r.scenario.endpoint_key,
                    'role': r.scenario.role.value,
                    'expected_access': r.scenario.access_level.value,
                    'actual_status': r.actual_status_code,
                    'access_correct': r.access_correct,
                    'violation_type': r.violation_type
                }
                for r in test_results
            ]
        }

    async def test_error_scenarios(
        self,
        endpoints: List[Dict[str, Any]],
        documented_errors: Optional[Dict[str, List]] = None,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test error scenarios for documented error conditions

        Validates:
        1. Each documented error condition can be triggered
        2. Error responses have required fields
        3. Error messages are helpful (not generic)
        4. Error format is consistent
        5. Error details provide context

        Args:
            endpoints: List of endpoint dicts
            documented_errors: Optional dict of custom error conditions per endpoint
            base_url: API base URL (defaults to http://localhost:8000)
            auth_token: Optional auth token for requests

        Returns:
            Dict with error quality results and summary
        """
        logger.info("=" * 80)
        logger.info("🔥 TESTING ERROR SCENARIOS")
        logger.info("=" * 80)
        logger.info("")

        # Set defaults
        if base_url is None:
            base_url = "http://localhost:8000"

        # Build headers
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        # Step 1: Generate error scenarios
        logger.info("📋 Generating error scenarios...")
        generator = ErrorScenarioGenerator(documented_errors)

        all_scenarios = generator.generate_all_error_scenarios(endpoints)

        # Show summary
        summary = generator.get_summary(all_scenarios)
        logger.info(f"   Total scenarios: {summary['total_scenarios']}")
        logger.info(f"   Error categories: {summary['unique_categories']}")
        logger.info(f"   Status codes: {summary['unique_status_codes']}")
        logger.info("")

        logger.info("📊 Scenarios by category:")
        for category, count in summary['by_category'].items():
            logger.info(f"   {category}: {count} scenarios")
        logger.info("")

        logger.info("📊 Scenarios by status code:")
        for code, count in sorted(summary['by_status_code'].items()):
            logger.info(f"   {code}: {count} scenarios")
        logger.info("")

        # Step 2: Validate error scenarios
        logger.info("🧪 Validating error scenarios...")
        logger.info("")

        validator = ErrorResponseValidator(
            base_url=base_url,
            default_headers=headers,
            timeout=30
        )

        test_results = await validator.validate_all_scenarios(all_scenarios)

        # Step 3: Generate quality report
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 ERROR QUALITY ANALYSIS")
        logger.info("=" * 80)
        logger.info("")

        quality_summary = validator.get_quality_summary()

        if 'error' in quality_summary:
            logger.error(f"❌ {quality_summary['error']}")
            return {'error': quality_summary['error']}

        total = quality_summary['total_scenarios']
        avg_score = quality_summary['average_quality_score']
        high_quality = quality_summary['high_quality_count']
        medium_quality = quality_summary['medium_quality_count']
        low_quality = quality_summary['low_quality_count']

        logger.info(f"Total Error Scenarios: {total}")
        logger.info(f"Average Quality Score: {avg_score:.0%}")
        logger.info("")

        logger.info("Quality Distribution:")
        logger.info(f"   ✅ High Quality (≥70%): {high_quality} ({high_quality/total*100:.1f}%)")
        logger.info(f"   ⚠️  Medium Quality (40-70%): {medium_quality} ({medium_quality/total*100:.1f}%)")
        logger.info(f"   ❌ Low Quality (<40%): {low_quality} ({low_quality/total*100:.1f}%)")
        logger.info("")

        # Show common issues
        if quality_summary['total_issues'] > 0:
            logger.info(f"Common Quality Issues ({quality_summary['total_issues']} total):")
            for issue_type, count in sorted(
                quality_summary['issue_breakdown'].items(),
                key=lambda x: -x[1]
            )[:5]:
                logger.info(f"   {issue_type}: {count} occurrences")
            logger.info("")

        # Show detailed report
        logger.info("=" * 80)
        detailed_report = validator.generate_quality_report()
        print(detailed_report)

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ ERROR SCENARIO TESTING COMPLETE")
        logger.info("=" * 80)
        logger.info("")

        # Return comprehensive results
        return {
            'total_scenarios': total,
            'average_quality_score': avg_score,
            'quality_distribution': {
                'high_quality': high_quality,
                'medium_quality': medium_quality,
                'low_quality': low_quality
            },
            'total_issues': quality_summary['total_issues'],
            'issue_breakdown': quality_summary['issue_breakdown'],
            'test_results': [
                {
                    'endpoint': r.scenario.endpoint_key,
                    'error_condition': r.scenario.error_condition.condition_name,
                    'expected_status': r.scenario.error_condition.expected_status_code,
                    'actual_status': r.actual_status_code,
                    'status_matches': r.status_code_matches,
                    'has_required_fields': r.has_required_fields,
                    'quality_score': r.message_quality_score,
                    'issues': [
                        {
                            'type': issue.issue_type,
                            'severity': issue.severity,
                            'description': issue.description
                        }
                        for issue in r.quality_issues
                    ]
                }
                for r in test_results
            ]
        }

    async def validate_schemas(
        self,
        endpoints: List[Dict[str, Any]],
        openapi_spec: Dict[str, Any],
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Validate API responses against OpenAPI schemas

        Tests each endpoint and validates responses match documented schemas.
        Detects schema violations like missing fields, wrong types, invalid formats.

        Args:
            endpoints: List of endpoint dicts
            openapi_spec: OpenAPI specification as dict
            base_url: API base URL (defaults to http://localhost:8000)
            auth_token: Optional auth token for requests
            strict_mode: If True, reject unexpected fields

        Returns:
            Dict with validation results and summary
        """
        logger.info("=" * 80)
        logger.info("📋 VALIDATING API RESPONSES AGAINST SCHEMAS")
        logger.info("=" * 80)
        logger.info("")

        # Set defaults
        if base_url is None:
            base_url = "http://localhost:8000"

        # Build headers
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        # Step 1: Parse OpenAPI spec
        logger.info("📖 Parsing OpenAPI specification...")
        parser = OpenAPISchemaParser(openapi_spec)

        endpoint_schemas = parser.extract_endpoint_schemas()
        logger.info(f"   Extracted schemas for {len(endpoint_schemas)} endpoints")
        logger.info("")

        # Step 2: Initialize validator
        logger.info(f"🔍 Initializing schema validator (strict_mode={strict_mode})...")
        validator = SchemaValidator(strict_mode=strict_mode)
        logger.info("")

        # Step 3: Test each endpoint and validate response
        logger.info("🧪 Testing endpoints and validating responses...")
        logger.info("")

        validation_results = []

        async with httpx.AsyncClient(timeout=30) as client:
            for endpoint in endpoints:
                method = endpoint.get('method', 'GET')
                path = endpoint.get('path', '')
                endpoint_key = f"{method} {path}"

                logger.info(f"Testing: {endpoint_key}")

                # Get schema for this endpoint
                endpoint_schema = endpoint_schemas.get(endpoint_key)

                if not endpoint_schema:
                    logger.warning(f"   ⚠️  No schema found in OpenAPI spec")
                    validation_results.append({
                        'endpoint': endpoint_key,
                        'schema_found': False,
                        'tested': False,
                        'reason': 'No schema in OpenAPI spec'
                    })
                    logger.info("")
                    continue

                try:
                    # Make request
                    url = base_url + path
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers
                    )

                    status_code = response.status_code
                    logger.info(f"   Response: {status_code}")

                    # Get expected schema for this status code
                    response_schema = endpoint_schema.response_schemas.get(status_code)

                    if not response_schema:
                        # Try to find closest match (e.g., 2XX for 200)
                        response_schema = endpoint_schema.response_schemas.get(200)

                    if not response_schema:
                        logger.warning(f"   ⚠️  No schema defined for status {status_code}")
                        validation_results.append({
                            'endpoint': endpoint_key,
                            'schema_found': True,
                            'status_code': status_code,
                            'tested': False,
                            'reason': f'No schema for status {status_code}'
                        })
                        logger.info("")
                        continue

                    # Parse response
                    try:
                        response_data = response.json()
                    except Exception:
                        logger.warning(f"   ⚠️  Response is not JSON")
                        validation_results.append({
                            'endpoint': endpoint_key,
                            'schema_found': True,
                            'status_code': status_code,
                            'tested': False,
                            'reason': 'Response is not JSON'
                        })
                        logger.info("")
                        continue

                    # Validate against schema
                    result: ValidationResult = validator.validate(
                        response_data,
                        response_schema,
                        field_path=endpoint_key
                    )

                    if result.valid:
                        logger.info(f"   ✅ Schema validation passed")
                    else:
                        logger.error(f"   ❌ Schema validation failed ({len(result.violations)} violations)")
                        for v in result.violations[:3]:  # Show first 3
                            logger.error(f"      • {v.description}")

                    validation_results.append({
                        'endpoint': endpoint_key,
                        'schema_found': True,
                        'status_code': status_code,
                        'tested': True,
                        'valid': result.valid,
                        'violations': [
                            {
                                'type': v.violation_type.value,
                                'severity': v.severity.value,
                                'field_path': v.field_path,
                                'expected': v.expected,
                                'actual': v.actual,
                                'description': v.description
                            }
                            for v in result.violations
                        ],
                        'violation_count': len(result.violations),
                        'critical_count': len(result.critical_violations),
                        'high_count': len(result.high_violations)
                    })

                except Exception as e:
                    logger.error(f"   ❌ Request failed: {str(e)}")
                    validation_results.append({
                        'endpoint': endpoint_key,
                        'schema_found': True,
                        'tested': False,
                        'reason': f'Request failed: {str(e)}'
                    })

                logger.info("")

        # Step 4: Generate summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 SCHEMA VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info("")

        total_endpoints = len(validation_results)
        tested = len([r for r in validation_results if r.get('tested')])
        valid = len([r for r in validation_results if r.get('valid')])
        invalid = len([r for r in validation_results if r.get('tested') and not r.get('valid')])
        not_tested = total_endpoints - tested

        logger.info(f"Total Endpoints: {total_endpoints}")
        logger.info(f"   Tested: {tested}")
        logger.info(f"   Not Tested: {not_tested}")
        logger.info("")

        if tested > 0:
            logger.info(f"Validation Results:")
            logger.info(f"   ✅ Valid: {valid} ({valid/tested*100:.1f}%)")
            logger.info(f"   ❌ Invalid: {invalid} ({invalid/tested*100:.1f}%)")
            logger.info("")

        # Show violations summary
        total_violations = sum(r.get('violation_count', 0) for r in validation_results)
        total_critical = sum(r.get('critical_count', 0) for r in validation_results)
        total_high = sum(r.get('high_count', 0) for r in validation_results)

        if total_violations > 0:
            logger.info(f"Total Violations: {total_violations}")
            logger.info(f"   Critical: {total_critical}")
            logger.info(f"   High: {total_high}")
            logger.info("")

        # Show failed endpoints
        if invalid > 0:
            logger.info("❌ Endpoints with schema violations:")
            for r in validation_results:
                if r.get('tested') and not r.get('valid'):
                    endpoint = r['endpoint']
                    v_count = r.get('violation_count', 0)
                    logger.info(f"   • {endpoint}: {v_count} violations")
            logger.info("")

        logger.info("=" * 80)
        logger.info("✅ SCHEMA VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info("")

        # Return comprehensive results
        return {
            'total_endpoints': total_endpoints,
            'tested': tested,
            'not_tested': not_tested,
            'valid': valid,
            'invalid': invalid,
            'total_violations': total_violations,
            'total_critical': total_critical,
            'total_high': total_high,
            'validation_results': validation_results
        }

    async def test_with_adaptive_learning(
        self,
        endpoints: List[Dict[str, Any]],
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        iterations: int = 3,
        merge_strategy: str = 'aggressive'
    ) -> Dict[str, Any]:
        """
        Run tests with adaptive learning enabled

        Tests endpoints multiple times, learning constraints from error responses
        and improving test data generation over time.

        Args:
            endpoints: List of endpoint dicts
            base_url: API base URL (defaults to http://localhost:8000)
            auth_token: Optional auth token for requests
            iterations: Number of learning iterations (default: 3)
            merge_strategy: How to merge learned constraints ('conservative', 'aggressive')

        Returns:
            Dict with learning results and final constraints
        """
        logger.info("=" * 80)
        logger.info("🧠 ADAPTIVE LEARNING MODE")
        logger.info("=" * 80)
        logger.info("")

        # Set defaults
        if base_url is None:
            base_url = "http://localhost:8000"

        # Build headers
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        # Initialize learning components
        learner = ConstraintLearner(min_confidence=0.7)
        updater = ConstraintUpdater()

        # Track constraints across iterations
        current_constraints = self.parameter_constraints or {}
        iteration_results = []

        logger.info(f"Starting adaptive learning with {iterations} iterations")
        logger.info(f"Merge strategy: {merge_strategy}")
        logger.info(f"Initial constraints: {len(current_constraints)} fields")
        logger.info("")

        # Learning iterations
        async with httpx.AsyncClient(timeout=30) as client:
            for iteration in range(1, iterations + 1):
                logger.info("=" * 80)
                logger.info(f"ITERATION {iteration}/{iterations}")
                logger.info("=" * 80)
                logger.info("")

                errors_found = 0
                constraints_learned = 0

                # Test each endpoint
                for endpoint in endpoints:
                    method = endpoint.get('method', 'GET')
                    path = endpoint.get('path', '')
                    endpoint_key = f"{method} {path}"

                    logger.info(f"Testing: {endpoint_key}")

                    # Generate test payload using current constraints
                    if method in ['POST', 'PUT', 'PATCH']:
                        # Simple test payload (in real usage, would use TestGenerator)
                        test_payload = {"test": "data"}
                    else:
                        test_payload = None

                    try:
                        # Make request
                        url = base_url + path
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            json=test_payload if test_payload else None
                        )

                        status_code = response.status_code
                        logger.info(f"   Response: {status_code}")

                        # Learn from error responses (4xx, 5xx)
                        if 400 <= status_code < 600:
                            errors_found += 1

                            try:
                                response_data = response.json()

                                # Learn constraints from error
                                learner.learn_from_error_response(
                                    response_body=response_data,
                                    status_code=status_code,
                                    endpoint=endpoint_key
                                )

                                # Get learned constraints for this endpoint
                                endpoint_constraints = learner.get_constraints_for_endpoint(endpoint_key)

                                if endpoint_constraints:
                                    constraints_learned += len(endpoint_constraints)
                                    logger.info(f"   📚 Learned {len(endpoint_constraints)} constraints")

                            except Exception as e:
                                logger.debug(f"   Could not parse error response: {e}")

                    except Exception as e:
                        logger.error(f"   ❌ Request failed: {str(e)}")

                    logger.info("")

                # Update constraints after iteration
                logger.info(f"Iteration {iteration} complete:")
                logger.info(f"   Errors found: {errors_found}")
                logger.info(f"   Constraints learned: {constraints_learned}")
                logger.info("")

                if constraints_learned > 0:
                    # Get all learned constraints
                    all_learned = learner.get_all_constraints()

                    # Merge with current constraints
                    for endpoint_key, field_constraints in all_learned.items():
                        if endpoint_key != 'global':
                            # Endpoint-specific constraints
                            logger.info(f"Updating constraints for {endpoint_key}...")

                        updated = updater.update_constraints(
                            existing_constraints=current_constraints,
                            learned_constraints=field_constraints,
                            merge_strategy=merge_strategy
                        )

                        current_constraints = updated

                    logger.info(f"✅ Updated constraints ({len(current_constraints)} fields total)")
                    logger.info("")

                # Store iteration results
                iteration_results.append({
                    'iteration': iteration,
                    'errors_found': errors_found,
                    'constraints_learned': constraints_learned,
                    'total_constraints': len(current_constraints)
                })

        # Final summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 ADAPTIVE LEARNING SUMMARY")
        logger.info("=" * 80)
        logger.info("")

        learning_stats = learner.get_statistics()
        update_summary = updater.get_update_summary()

        logger.info(f"Total Iterations: {iterations}")
        logger.info(f"Total Errors Processed: {learning_stats['total_errors_processed']}")
        logger.info(f"Total Constraints Learned: {learning_stats['total_constraints_learned']}")
        logger.info(f"High Confidence Constraints: {learning_stats['high_confidence_count']}")
        logger.info("")

        logger.info("Constraints by Type:")
        for constraint_type, count in learning_stats.get('constraints_by_type', {}).items():
            logger.info(f"   {constraint_type}: {count}")
        logger.info("")

        logger.info("Updates Applied:")
        for update_type, count in update_summary['by_type'].items():
            logger.info(f"   {update_type}: {count}")
        logger.info("")

        logger.info(f"Fields Affected: {len(update_summary['fields_affected'])}")
        logger.info(f"Final Constraint Count: {len(current_constraints)} fields")
        logger.info("")

        # Show iteration progress
        logger.info("Learning Progress:")
        for result in iteration_results:
            logger.info(
                f"   Iteration {result['iteration']}: "
                f"{result['errors_found']} errors → "
                f"{result['constraints_learned']} constraints learned → "
                f"{result['total_constraints']} total"
            )
        logger.info("")

        logger.info("=" * 80)
        logger.info("✅ ADAPTIVE LEARNING COMPLETE")
        logger.info("=" * 80)
        logger.info("")

        # Return comprehensive results
        return {
            'iterations': iterations,
            'learning_stats': learning_stats,
            'update_summary': update_summary,
            'iteration_results': iteration_results,
            'final_constraints': current_constraints,
            'learned_constraints': learner.export_constraints(),
            'improvement_rate': (
                iteration_results[-1]['total_constraints'] - iteration_results[0]['total_constraints']
            ) if len(iteration_results) > 1 else 0
        }

    def cleanup(self):
        """Clean up resources"""
        if self.flow_store:
            self.flow_store.cleanup()
        logger.info(f"Cleaned up test session: {self.session_id}")
