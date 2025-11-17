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
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
        method = endpoint.get('method', 'GET').upper()
        url = f"{self.base_url}{endpoint.get('path', '')}"

        logger.info(f"   URL: {url}")
        logger.info(f"   Method: {method}")

        # Store request in Flow DB
        self.flow_store.store_request(endpoint_key, payload, {"attempt": attempt})

        start_time = time.time()

        try:
            # Execute request based on method
            if method == 'GET':
                # Add payload as query params for GET
                if payload:
                    query_string = urlencode(payload)
                    url = f"{url}?{query_string}"
                response = await self.client.get(url, headers=headers)

            elif method == 'POST':
                logger.info(f"   Payload: {str(payload)[:200]}...")
                response = await self.client.post(url, headers=headers, json=payload)

            elif method == 'PUT':
                logger.info(f"   Payload: {str(payload)[:200]}...")
                response = await self.client.put(url, headers=headers, json=payload)

            elif method == 'PATCH':
                logger.info(f"   Payload: {str(payload)[:200]}...")
                response = await self.client.patch(url, headers=headers, json=payload)

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
                'final_payload': payload,
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

    def cleanup(self):
        """Clean up resources"""
        if self.flow_store:
            self.flow_store.cleanup()
        logger.info(f"Cleaned up test session: {self.session_id}")
