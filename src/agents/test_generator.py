"""
Test Generator Agent
Generates test case payloads using RAG and Flow DB context
"""
import json
import random
import string
from typing import Dict, Any, Optional

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

from src.agents.base_agent import BaseAgent
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore


class TestGenerator(BaseAgent):
    """
    Agent that generates test case payloads
    Uses RAG to retrieve relevant documentation and Flow DB for previous data
    """

    def __init__(
        self,
        doc_store: DocumentStore,
        flow_store: Optional[FlowStore] = None
    ):
        """
        Initialize Test Generator

        Args:
            doc_store: Document store for RAG retrieval
            flow_store: Optional flow store for accessing previous test data
        """
        super().__init__(agent_name="TestGenerator", use_fast_llm=False)
        self.doc_store = doc_store
        self.flow_store = flow_store

    def generate_test_payload(
        self,
        endpoint: Dict[str, Any],
        test_type: str = "positive"
    ) -> Dict[str, Any]:
        """
        Generate test payload for an endpoint

        Args:
            endpoint: Endpoint dict with path, method, parameters, etc.
            test_type: "positive", "negative", or "boundary"

        Returns:
            Test payload dict
        """
        endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
        logger.info(f"Generating {test_type} test payload for: {endpoint_key}")

        # Step 1: Retrieve relevant documentation via RAG
        doc_context = self._retrieve_documentation_context(endpoint)

        # Step 2: Query Flow DB for previous data if available
        flow_context = ""
        if self.flow_store:
            flow_context = self._retrieve_flow_context(endpoint)

        # Step 3: Generate payload using LLM
        payload = self._generate_payload_with_llm(
            endpoint, doc_context, flow_context, test_type
        )

        logger.info(f"✅ Generated {test_type} payload: {json.dumps(payload)[:100]}...")

        return payload

    def _retrieve_documentation_context(
        self,
        endpoint: Dict[str, Any]
    ) -> str:
        """
        Retrieve relevant documentation using RAG

        Args:
            endpoint: Endpoint dict

        Returns:
            Combined context string
        """
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        # Build search query
        query = f"API endpoint {endpoint_key} parameters request payload example"

        # Search documentation
        results = self.doc_store.query(query, n_results=3)

        if not results['documents']:
            logger.warning(f"No documentation found for {endpoint_key}")
            return ""

        # Combine top results
        context = "\n\n---\n\n".join(results['documents'])

        logger.debug(f"Retrieved {len(results['documents'])} documentation chunks")

        return context

    def _retrieve_flow_context(self, endpoint: Dict[str, Any]) -> str:
        """
        Retrieve previous test execution data from Flow DB

        Args:
            endpoint: Endpoint dict

        Returns:
            Context string from previous API calls
        """
        if not self.flow_store:
            return ""

        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        # Build query based on what this endpoint might need
        query_parts = []

        # If auth required, look for tokens/credentials
        if endpoint.get('auth_required'):
            query_parts.append("authentication token bearer credential")

        # Look for IDs, codes, etc.
        path_lower = endpoint.get('path', '').lower()
        if 'id' in path_lower:
            query_parts.append("user_id id identifier")
        if 'code' in path_lower:
            query_parts.append("code verification_code")

        query = " ".join(query_parts) or "previous successful API responses"

        # Search flow data
        context = self.flow_store.query_for_context(query, n_results=2)

        if context and context != "No previous flow data found.":
            logger.debug("Retrieved context from Flow DB")

        return context

    def _generate_payload_with_llm(
        self,
        endpoint: Dict[str, Any],
        doc_context: str,
        flow_context: str,
        test_type: str
    ) -> Dict[str, Any]:
        """
        Generate payload using LLM with context

        Args:
            endpoint: Endpoint dict
            doc_context: Documentation context from RAG
            flow_context: Previous test data from Flow DB
            test_type: Type of test

        Returns:
            Generated payload dict
        """
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"

        # Generate unique values for signup/registration
        unique_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        system_prompt = f"""You are an expert API testing assistant.
Generate a complete test payload for API testing.

Guidelines:
1. Use previous data from Flow Context when available (credentials, tokens, IDs)
2. For passwords: Use ORIGINAL plain text password from signup REQUEST, NOT hashed version
3. Extract ALL required fields from documentation
4. For unique fields (email, username): Generate with suffix '{unique_suffix}'
5. Match exact field names and types from documentation
6. Return ONLY valid JSON payload"""

        user_prompt = f"""Generate a {test_type} test payload for this API endpoint.

Endpoint: {endpoint_key}
Method: {endpoint.get('method', 'GET')}
Summary: {endpoint.get('summary', 'N/A')}

Parameters from API spec:
{json.dumps(endpoint.get('parameters', []), indent=2)}

PREVIOUS API CALLS DATA (Flow DB):
{flow_context or 'No previous data available'}

Documentation Context:
{doc_context or 'No additional documentation'}

TEST TYPE: {test_type}
- positive: Valid data that should succeed
- negative: Invalid data that should fail
- boundary: Edge cases and limits

UNIQUE SUFFIX for this test: {unique_suffix}
Use format: test_{unique_suffix}@example.com for emails

Return ONLY the JSON payload (for GET requests, these will be query params):
{{"field": "value"}}

NO markdown, NO explanations, ONLY JSON."""

        try:
            response = self.invoke(user_prompt, system_prompt)
            payload = self.parse_json_response(response)

            # Validate payload has content
            if not payload:
                logger.warning(f"Empty payload generated for {endpoint_key}")
                return {}

            return payload

        except Exception as e:
            logger.error(f"Failed to generate payload: {e}")
            # Return minimal payload based on parameters
            return self._generate_fallback_payload(endpoint, unique_suffix)

    def _generate_fallback_payload(
        self,
        endpoint: Dict[str, Any],
        unique_suffix: str
    ) -> Dict[str, Any]:
        """
        Generate basic fallback payload if LLM fails

        Args:
            endpoint: Endpoint dict
            unique_suffix: Unique suffix for test data

        Returns:
            Basic payload dict
        """
        payload = {}

        for param in endpoint.get('parameters', []):
            name = param.get('name')
            param_type = param.get('type', 'string')
            required = param.get('required', False)

            if not required:
                continue

            # Generate basic values by type
            if param_type == 'string':
                if 'email' in name.lower():
                    payload[name] = f"test_{unique_suffix}@example.com"
                elif 'password' in name.lower():
                    payload[name] = f"Test{unique_suffix}@123"
                elif 'phone' in name.lower() or 'mobile' in name.lower():
                    payload[name] = f"9{random.randint(100000000, 999999999)}"
                else:
                    payload[name] = f"test_{unique_suffix}"

            elif param_type == 'integer' or param_type == 'number':
                payload[name] = random.randint(1, 100)

            elif param_type == 'boolean':
                payload[name] = True

        logger.warning(f"Using fallback payload: {payload}")
        return payload

    def generate_test_variations(
        self,
        endpoint: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate multiple test variations for an endpoint

        Args:
            endpoint: Endpoint dict

        Returns:
            Dict with test_type as key and payload as value
        """
        variations = {}

        # Generate different test types
        for test_type in ["positive", "negative", "boundary"]:
            try:
                payload = self.generate_test_payload(endpoint, test_type)
                variations[test_type] = payload
            except Exception as e:
                logger.warning(f"Failed to generate {test_type} test: {e}")

        return variations
