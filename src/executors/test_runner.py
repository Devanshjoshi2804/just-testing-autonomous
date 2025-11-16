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
        semantic_contexts: Optional[Dict] = None
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
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = session_id
        self.doc_store = doc_store
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.use_rl = use_rl
        self.semantic_contexts = semantic_contexts

        # Initialize Flow Store for this session
        self.flow_store = FlowStore(session_id=session_id)

        # Initialize agents
        self.analyzer = EndpointAnalyzer()

        # Use EnhancedTestGenerator if semantic contexts available
        if semantic_contexts:
            self.generator = EnhancedTestGenerator(
                doc_store,
                self.flow_store,
                semantic_contexts=semantic_contexts
            )
            logger.info(f"🧠 Using EnhancedTestGenerator with semantic contexts for {len(semantic_contexts)} endpoints")
        else:
            self.generator = TestGenerator(doc_store, self.flow_store)
            logger.info("Using standard TestGenerator")

        self.fixer = ErrorFixer(doc_store, self.flow_store)

        # Initialize RL optimizer
        if use_rl:
            self.rl_optimizer = TestOptimizer()
            logger.info("🧠 RL Test Optimizer enabled")
        else:
            self.rl_optimizer = None
            logger.info("Traditional test ordering enabled")

        # Test results
        self.results = []

        # Endpoint metadata tracking for RL
        self.endpoint_metadata = {}

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
            "results": self.results,
        }

    def cleanup(self):
        """Clean up resources"""
        if self.flow_store:
            self.flow_store.cleanup()
        logger.info(f"Cleaned up test session: {self.session_id}")
