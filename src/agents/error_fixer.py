"""
Error Fixer Agent
Analyzes failed API tests and generates fixes using Flow DB context
"""
import json
import random
import string
from typing import Dict, Any
from loguru import logger

from src.agents.base_agent import BaseAgent
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore


class ErrorFixer(BaseAgent):
    """
    Agent that analyzes API test failures and generates fixes
    Uses Flow DB to retrieve context and documentation for intelligent retry
    """

    def __init__(
        self,
        doc_store: DocumentStore,
        flow_store: FlowStore
    ):
        """
        Initialize Error Fixer

        Args:
            doc_store: Document store for documentation context
            flow_store: Flow store for previous test data
        """
        super().__init__(agent_name="ErrorFixer", use_fast_llm=True)  # Use fast model
        self.doc_store = doc_store
        self.flow_store = flow_store

    def fix_failed_test(
        self,
        endpoint: Dict[str, Any],
        original_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        status_code: int
    ) -> Dict[str, Any]:
        """
        Analyze failure and generate fixed payload

        Args:
            endpoint: Endpoint dict
            original_payload: The payload that failed
            error_response: Error response from API
            status_code: HTTP status code

        Returns:
            Fixed payload dict
        """
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
        logger.info(f"Analyzing failure for: {endpoint_key} (status={status_code})")

        # Step 1: Retrieve documentation context
        doc_context = self._retrieve_doc_context(endpoint)

        # Step 2: Query Flow DB for relevant data
        flow_context = self._retrieve_fix_context(endpoint, error_response)

        # Step 3: Generate fix using LLM
        fixed_payload = self._generate_fix_with_llm(
            endpoint,
            original_payload,
            error_response,
            status_code,
            doc_context,
            flow_context
        )

        logger.info(f"✅ Generated fix: {json.dumps(fixed_payload)[:100]}...")

        return fixed_payload

    def _retrieve_doc_context(self, endpoint: Dict[str, Any]) -> str:
        """
        Retrieve relevant documentation for fixing errors

        Args:
            endpoint: Endpoint dict

        Returns:
            Documentation context
        """
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        # Search for error handling documentation
        query = (
            f"{endpoint_key} error response validation "
            f"required fields parameters"
        )

        results = self.doc_store.query(query, n_results=2)

        if results['documents']:
            context = "\n\n".join(results['documents'])
            logger.debug("Retrieved documentation context for error fixing")
            return context

        return ""

    def _retrieve_fix_context(
        self,
        endpoint: Dict[str, Any],
        error_response: Dict[str, Any]
    ) -> str:
        """
        Query Flow DB for data to fix the error

        Args:
            endpoint: Endpoint dict
            error_response: Error response

        Returns:
            Relevant context from previous successful API calls
        """
        # Analyze error to determine what data is needed
        error_str = str(error_response).lower()

        query_parts = []

        # Common error patterns and what to look for
        if any(term in error_str for term in ['token', 'unauthorized', 'authentication']):
            query_parts.append("authentication token bearer credentials login")

        if any(term in error_str for term in ['user', 'user_id']):
            query_parts.append("user_id user identifier from signup")

        if 'password' in error_str:
            query_parts.append("password from signup REQUEST plain text")

        if any(term in error_str for term in ['email', 'exists', 'already']):
            query_parts.append("email address username")

        if any(term in error_str for term in ['required', 'missing']):
            query_parts.append("required fields parameters successful requests")

        # Build query
        query = " ".join(query_parts) or "successful API responses with all fields"

        # Search flow data
        context = self.flow_store.query_for_context(query, n_results=3)

        if context and context != "No previous flow data found.":
            logger.debug("Found relevant context in Flow DB for fixing error")

        return context

    def _generate_fix_with_llm(
        self,
        endpoint: Dict[str, Any],
        original_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        status_code: int,
        doc_context: str,
        flow_context: str
    ) -> Dict[str, Any]:
        """
        Generate fixed payload using LLM

        Args:
            endpoint: Endpoint dict
            original_payload: Original failed payload
            error_response: Error response
            status_code: Status code
            doc_context: Documentation context
            flow_context: Flow DB context

        Returns:
            Fixed payload
        """
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
        unique_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        system_prompt = """You are an expert API debugging assistant.
Analyze the failed API test and generate a FIXED payload.

Rules:
1. Extract needed data from Flow Context (tokens, IDs, credentials)
2. For passwords: Use ORIGINAL plain text from signup REQUEST, NOT hashed
3. If field is missing: Add it with correct value
4. If value is invalid: Replace with valid value from documentation
5. If duplicate error: Generate NEW unique values
6. Keep all correct fields from original payload
7. Return ONLY the fixed JSON payload"""

        user_prompt = f"""Fix this failed API test.

Endpoint: {endpoint_key}
Status Code: {status_code}

Original Payload (FAILED):
{json.dumps(original_payload, indent=2)}

Error Response:
{json.dumps(error_response, indent=2)}

FLOW CONTEXT (Previous successful API calls):
{flow_context or 'No previous data available'}

Documentation Context:
{doc_context or 'No additional documentation'}

UNIQUE SUFFIX for new values: {unique_suffix}

Analyze the error and generate the FIXED payload.
Return ONLY the corrected JSON payload:
{{"field": "value"}}

NO markdown, NO explanations, ONLY the fixed JSON."""

        try:
            response = self.invoke(user_prompt, system_prompt)
            fixed_payload = self.parse_json_response(response)

            # Validate fix has changes
            if fixed_payload == original_payload:
                logger.warning("Fix is identical to original, applying heuristics")
                fixed_payload = self._apply_fix_heuristics(
                    original_payload, error_response, unique_suffix
                )

            return fixed_payload

        except Exception as e:
            logger.error(f"Failed to generate fix with LLM: {e}")
            # Fallback to heuristic fixes
            return self._apply_fix_heuristics(
                original_payload, error_response, unique_suffix
            )

    def _apply_fix_heuristics(
        self,
        original_payload: Dict[str, Any],
        error_response: Dict[str, Any],
        unique_suffix: str
    ) -> Dict[str, Any]:
        """
        Apply heuristic fixes based on common error patterns

        Args:
            original_payload: Original payload
            error_response: Error response
            unique_suffix: Unique suffix for new values

        Returns:
            Fixed payload
        """
        fixed = original_payload.copy()
        error_str = str(error_response).lower()

        logger.info("Applying heuristic fixes...")

        # Fix: Duplicate user/email error
        if any(term in error_str for term in ['exists', 'already', 'duplicate']):
            logger.info("Detected duplicate error, generating new unique values")

            for key in fixed:
                if 'email' in key.lower():
                    fixed[key] = f"test_{unique_suffix}@example.com"
                elif 'username' in key.lower():
                    fixed[key] = f"user_{unique_suffix}"
                elif 'phone' in key.lower() or 'mobile' in key.lower():
                    fixed[key] = f"9{random.randint(100000000, 999999999)}"

        # Fix: Missing required field
        elif 'required' in error_str or 'missing' in error_str:
            logger.info("Detected missing field error")

            # Try to extract field name from error
            import re
            field_match = re.search(r'["\'](\w+)["\']', str(error_response))
            if field_match:
                missing_field = field_match.group(1)
                logger.info(f"Adding missing field: {missing_field}")
                fixed[missing_field] = f"test_{unique_suffix}"

        # Fix: Invalid format
        elif 'invalid' in error_str or 'format' in error_str:
            logger.info("Detected invalid format error")

            for key in fixed:
                if 'email' in key.lower() and '@' not in str(fixed[key]):
                    fixed[key] = f"{fixed[key]}@example.com"

        return fixed

    def should_retry(self, status_code: int, error_response: Dict[str, Any]) -> bool:
        """
        Determine if this error is worth retrying

        Args:
            status_code: HTTP status code
            error_response: Error response

        Returns:
            True if should retry
        """
        # Don't retry server errors (500+) - likely not our fault
        if status_code >= 500:
            logger.info(f"Server error ({status_code}), not retrying")
            return False

        # Don't retry authentication failures after first attempt
        # (unless we can get new credentials)
        if status_code == 401:
            # Only retry if we have a way to get new token
            if self.flow_store:
                successful = self.flow_store.get_successful_responses()
                has_auth = any('token' in str(r).lower() for r in successful)
                if has_auth:
                    logger.info("401 but we have auth data, will retry")
                    return True

            logger.info("401 and no auth data, not retrying")
            return False

        # Retry client errors (400-499) - likely fixable
        if 400 <= status_code < 500:
            logger.info(f"Client error ({status_code}), will retry with fix")
            return True

        return False
