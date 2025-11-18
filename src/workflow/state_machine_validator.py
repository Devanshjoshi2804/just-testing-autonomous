"""
State Machine Validator
Executes state transition sequences and validates API behavior
Ensures API correctly handles state transitions and invalid operations
"""
import httpx
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
        def success(self, msg, **kwargs): print(f"SUCCESS: {msg}")
    logger = MockLogger()

from src.workflow.state_transition_generator import (
    TransitionSequence,
    StateTransition,
    TransitionType,
    ResourceState
)
from src.workflow.data_flow_tracker import DataFlowTracker


@dataclass
class TransitionResult:
    """Result of executing a single state transition"""
    transition: StateTransition
    status_code: int
    response_body: Dict[str, Any]
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    extracted_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SequenceResult:
    """Result of executing a complete transition sequence"""
    sequence: TransitionSequence
    transition_results: List[TransitionResult]
    overall_success: bool
    total_time_ms: float
    failure_reason: Optional[str] = None
    summary: str = ""


class StateMachineValidator:
    """
    Validates API state machine behavior by executing transition sequences

    Responsibilities:
    1. Execute state transition sequences
    2. Track resource IDs across transitions (CREATE → UPDATE → DELETE)
    3. Validate expected vs actual status codes
    4. Verify invalid transitions fail correctly
    5. Test idempotency (repeated operations)
    6. Generate detailed test reports
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Initialize validator

        Args:
            base_url: Base URL for API (e.g., "https://api.example.com")
            headers: Optional default headers (e.g., auth tokens)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout
        self.data_flow_tracker = DataFlowTracker()
        self.client = None

    async def validate_sequence(
        self,
        sequence: TransitionSequence,
        test_data_generator = None
    ) -> SequenceResult:
        """
        Execute and validate a complete state transition sequence

        Args:
            sequence: TransitionSequence to execute
            test_data_generator: Optional generator for test payloads

        Returns:
            SequenceResult with execution details
        """
        logger.info(f"🔄 Executing sequence: {sequence.description}")

        start_time = datetime.now()
        transition_results = []
        overall_success = True
        failure_reason = None

        # Clear data flow tracker for new sequence
        self.data_flow_tracker.clear()

        # Initialize HTTP client
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            self.client = client

            # Execute each transition in sequence
            for i, transition in enumerate(sequence.transitions):
                logger.debug(
                    f"  Step {i+1}/{len(sequence.transitions)}: {transition.description}"
                )

                # Execute transition
                result = await self._execute_transition(
                    transition,
                    sequence.resource_name,
                    test_data_generator
                )

                transition_results.append(result)

                # Check if transition succeeded/failed as expected
                if not self._validate_transition_result(transition, result):
                    overall_success = False
                    failure_reason = (
                        f"Step {i+1} failed: {transition.description}. "
                        f"Expected status {transition.expected_status_codes}, "
                        f"got {result.status_code}"
                    )
                    logger.error(f"  ❌ {failure_reason}")
                    # Continue executing remaining transitions to gather data
                else:
                    logger.success(
                        f"  ✅ Step {i+1} succeeded: {transition.description} "
                        f"(status: {result.status_code})"
                    )

        # Calculate total time
        end_time = datetime.now()
        total_time_ms = (end_time - start_time).total_seconds() * 1000

        # Generate summary
        summary = self._generate_sequence_summary(
            sequence,
            transition_results,
            overall_success
        )

        result = SequenceResult(
            sequence=sequence,
            transition_results=transition_results,
            overall_success=overall_success,
            total_time_ms=total_time_ms,
            failure_reason=failure_reason,
            summary=summary
        )

        if overall_success:
            logger.success(f"✅ Sequence completed successfully: {sequence.description}")
        else:
            logger.warning(f"⚠️  Sequence completed with issues: {sequence.description}")

        return result

    async def _execute_transition(
        self,
        transition: StateTransition,
        resource_name: str,
        test_data_generator = None
    ) -> TransitionResult:
        """
        Execute a single state transition

        Args:
            transition: StateTransition to execute
            resource_name: Resource name for data injection
            test_data_generator: Optional test data generator

        Returns:
            TransitionResult with execution details
        """
        start_time = datetime.now()

        # Build request URL
        path = transition.path
        if transition.requires_id:
            # Inject ID from data flow tracker
            path = self.data_flow_tracker.inject_into_path(path, resource_name)

            # If no ID was injected and transition expects non-existent resource, use fake ID
            if '{id}' in path or '{' in path:
                # Use a fake/non-existent ID for testing invalid transitions
                path = path.replace('{id}', 'nonexistent-id-12345')
                path = path.replace(f'{{{resource_name}_id}}', 'nonexistent-id-12345')

        url = f"{self.base_url}{path}"

        # Build request payload
        payload = None
        if transition.method in ['POST', 'PUT', 'PATCH']:
            if test_data_generator:
                # Use test data generator to create payload
                payload = test_data_generator.generate_payload(resource_name, transition.method)
            else:
                # Use simple default payload
                payload = self._generate_default_payload(resource_name, transition.method)

            # Inject IDs into payload if needed
            if payload:
                payload = self.data_flow_tracker.inject_into_body(payload, resource_name)

        # Execute HTTP request
        try:
            response = await self._make_request(
                method=transition.method,
                url=url,
                payload=payload
            )

            status_code = response.status_code
            response_body = self._parse_response_body(response)
            success = status_code in transition.expected_status_codes

            # Extract IDs from successful CREATE responses
            if (transition.method == 'POST' and
                200 <= status_code < 300 and
                response_body):
                extracted = self.data_flow_tracker.extract_from_response(
                    endpoint_key=transition.endpoint_key,
                    response_body=response_body,
                    status_code=status_code
                )
                logger.debug(f"  📥 Extracted {len(extracted)} values from response")

            error_message = None

        except Exception as e:
            logger.error(f"  ❌ Request failed: {str(e)}")
            status_code = 0
            response_body = {}
            success = False
            error_message = str(e)

        # Calculate response time
        end_time = datetime.now()
        response_time_ms = (end_time - start_time).total_seconds() * 1000

        return TransitionResult(
            transition=transition,
            status_code=status_code,
            response_body=response_body,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
            extracted_values=self.data_flow_tracker.get_extracted_summary()
        )

    async def _make_request(
        self,
        method: str,
        url: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request"""
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/json'

        logger.debug(f"  → {method} {url}")
        if payload:
            logger.debug(f"    Payload: {json.dumps(payload, indent=2)[:200]}...")

        if method == 'GET':
            response = await self.client.get(url, headers=headers)
        elif method == 'POST':
            response = await self.client.post(url, json=payload, headers=headers)
        elif method == 'PUT':
            response = await self.client.put(url, json=payload, headers=headers)
        elif method == 'PATCH':
            response = await self.client.patch(url, json=payload, headers=headers)
        elif method == 'DELETE':
            response = await self.client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        logger.debug(f"  ← Status: {response.status_code}")

        return response

    def _parse_response_body(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse response body to dict"""
        try:
            return response.json()
        except:
            # Return text as dict if not JSON
            return {"_raw_response": response.text}

    def _generate_default_payload(
        self,
        resource_name: str,
        method: str
    ) -> Dict[str, Any]:
        """
        Generate simple default payload for testing

        Args:
            resource_name: Resource name (e.g., "users")
            method: HTTP method

        Returns:
            Default test payload
        """
        if method == 'POST':
            # CREATE payload - generic test data
            return {
                'name': f'Test {resource_name} {uuid.uuid4().hex[:8]}',
                'description': f'Test {resource_name} for state transition testing',
                'status': 'active'
            }
        elif method in ['PUT', 'PATCH']:
            # UPDATE payload - modified test data
            return {
                'name': f'Updated {resource_name} {uuid.uuid4().hex[:8]}',
                'description': f'Updated {resource_name} for state transition testing',
                'status': 'updated'
            }
        return {}

    def _validate_transition_result(
        self,
        transition: StateTransition,
        result: TransitionResult
    ) -> bool:
        """
        Validate that transition result matches expectations

        Args:
            transition: Expected transition
            result: Actual result

        Returns:
            True if result matches expectations
        """
        # Check if status code matches expectations
        status_matches = result.status_code in transition.expected_status_codes

        if not status_matches:
            return False

        # For VALID transitions, verify success
        if transition.transition_type == TransitionType.VALID:
            return 200 <= result.status_code < 300

        # For INVALID transitions, verify failure
        if transition.transition_type == TransitionType.INVALID:
            return result.status_code >= 400

        # For IDEMPOTENT transitions, just verify expected status codes
        if transition.transition_type == TransitionType.IDEMPOTENT:
            return status_matches

        return True

    def _generate_sequence_summary(
        self,
        sequence: TransitionSequence,
        results: List[TransitionResult],
        overall_success: bool
    ) -> str:
        """Generate human-readable summary of sequence execution"""
        lines = []
        lines.append(f"Sequence: {sequence.description}")
        lines.append(f"Type: {sequence.sequence_type}")
        lines.append(f"Resource: {sequence.resource_name}")
        lines.append(f"Overall Success: {'✅ Yes' if overall_success else '❌ No'}")
        lines.append("")
        lines.append("Transitions:")

        for i, result in enumerate(results):
            transition = result.transition
            status_icon = "✅" if result.success else "❌"
            lines.append(
                f"  {i+1}. {status_icon} {transition.description} "
                f"({transition.method} {transition.path})"
            )
            lines.append(f"     Status: {result.status_code} (expected: {transition.expected_status_codes})")
            lines.append(f"     Time: {result.response_time_ms:.0f}ms")

            if result.error_message:
                lines.append(f"     Error: {result.error_message}")

        return "\n".join(lines)

    async def validate_multiple_sequences(
        self,
        sequences: List[TransitionSequence],
        test_data_generator = None
    ) -> List[SequenceResult]:
        """
        Validate multiple transition sequences

        Args:
            sequences: List of TransitionSequence to execute
            test_data_generator: Optional test data generator

        Returns:
            List of SequenceResult
        """
        logger.info(f"🔄 Validating {len(sequences)} state transition sequences...")

        results = []
        for i, sequence in enumerate(sequences):
            logger.info(f"\n{'='*60}")
            logger.info(f"Sequence {i+1}/{len(sequences)}")
            logger.info(f"{'='*60}")

            result = await self.validate_sequence(sequence, test_data_generator)
            results.append(result)

        # Generate overall summary
        total_sequences = len(results)
        successful_sequences = sum(1 for r in results if r.overall_success)
        failed_sequences = total_sequences - successful_sequences

        logger.info(f"\n{'='*60}")
        logger.info(f"STATE TRANSITION VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total sequences: {total_sequences}")
        logger.info(f"Successful: {successful_sequences} ✅")
        logger.info(f"Failed: {failed_sequences} ❌")
        logger.info(f"Success rate: {(successful_sequences/total_sequences*100):.1f}%")

        return results

    def get_validation_report(
        self,
        results: List[SequenceResult]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive validation report

        Args:
            results: List of SequenceResult

        Returns:
            Report dict with statistics and details
        """
        total_sequences = len(results)
        successful_sequences = sum(1 for r in results if r.overall_success)
        failed_sequences = total_sequences - successful_sequences

        total_transitions = sum(len(r.transition_results) for r in results)
        successful_transitions = sum(
            sum(1 for tr in r.transition_results if tr.success)
            for r in results
        )

        avg_time_ms = sum(r.total_time_ms for r in results) / total_sequences if total_sequences > 0 else 0

        # Group results by sequence type
        results_by_type = {}
        for result in results:
            seq_type = result.sequence.sequence_type
            if seq_type not in results_by_type:
                results_by_type[seq_type] = {'total': 0, 'passed': 0, 'failed': 0}

            results_by_type[seq_type]['total'] += 1
            if result.overall_success:
                results_by_type[seq_type]['passed'] += 1
            else:
                results_by_type[seq_type]['failed'] += 1

        return {
            'summary': {
                'total_sequences': total_sequences,
                'successful_sequences': successful_sequences,
                'failed_sequences': failed_sequences,
                'success_rate': (successful_sequences / total_sequences * 100) if total_sequences > 0 else 0,
                'total_transitions': total_transitions,
                'successful_transitions': successful_transitions,
                'avg_sequence_time_ms': avg_time_ms
            },
            'by_type': results_by_type,
            'failed_sequences': [
                {
                    'description': r.sequence.description,
                    'type': r.sequence.sequence_type,
                    'resource': r.sequence.resource_name,
                    'failure_reason': r.failure_reason
                }
                for r in results if not r.overall_success
            ]
        }
