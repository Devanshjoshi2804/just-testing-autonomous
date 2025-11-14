"""
Endpoint Analyzer Agent
Analyzes API documentation and extracts endpoint information using LLM
"""
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from src.agents.base_agent import BaseAgent


class EndpointAnalyzer(BaseAgent):
    """
    Agent that analyzes API documentation and extracts endpoints
    Uses LLM to understand documentation structure and extract API details
    """

    def __init__(self):
        """Initialize Endpoint Analyzer"""
        super().__init__(agent_name="EndpointAnalyzer", use_fast_llm=False)

    def analyze_documentation(
        self,
        doc_text: str,
        base_url: Optional[str] = None,
        chunk_size: int = 15000
    ) -> Dict[str, Any]:
        """
        Analyze documentation and extract all API endpoints

        Args:
            doc_text: Full documentation text
            base_url: Optional base URL (will try to extract if not provided)
            chunk_size: Max characters per LLM call

        Returns:
            Dict with:
                - base_url: API base URL
                - endpoints: List of endpoint dicts
                - summary: High-level API summary
        """
        logger.info(f"Analyzing documentation ({len(doc_text)} chars)...")

        # Split into chunks if needed
        text_chunks = [
            doc_text[i:i + chunk_size]
            for i in range(0, len(doc_text), chunk_size)
        ]

        logger.info(f"Processing {len(text_chunks)} documentation chunks")

        all_endpoints = []
        extracted_base_url = base_url

        # Process each chunk
        for idx, chunk in enumerate(text_chunks):
            logger.info(f"Analyzing chunk {idx + 1}/{len(text_chunks)}...")

            result = self._analyze_chunk(chunk, extracted_base_url)

            # Extract base URL from first chunk if not provided
            if not extracted_base_url and result.get("base_url"):
                extracted_base_url = result["base_url"]
                logger.info(f"Extracted base URL: {extracted_base_url}")

            # Add endpoints from this chunk
            if result.get("endpoints"):
                all_endpoints.extend(result["endpoints"])
                logger.info(f"Found {len(result['endpoints'])} endpoints in chunk")

        # Deduplicate endpoints by path+method
        unique_endpoints = self._deduplicate_endpoints(all_endpoints)

        logger.info(
            f"✅ Analysis complete: {len(unique_endpoints)} unique endpoints found"
        )

        return {
            "base_url": extracted_base_url,
            "endpoints": unique_endpoints,
            "summary": self._generate_api_summary(unique_endpoints),
        }

    def _analyze_chunk(
        self,
        chunk_text: str,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single documentation chunk

        Args:
            chunk_text: Documentation chunk
            base_url: Known base URL (optional)

        Returns:
            Dict with base_url and endpoints
        """
        system_prompt = """You are an expert API documentation analyzer.
Your task is to extract API endpoint information from documentation text.

Extract:
1. Base URL (if not provided)
2. All API endpoints with complete details

Be thorough and extract ALL endpoints mentioned."""

        user_prompt = f"""Analyze this API documentation and extract endpoint information.

{'Base URL: ' + base_url if base_url else 'Extract the base URL from the documentation.'}

Documentation:
{chunk_text}

Return ONLY valid JSON in this format:
{{
    "base_url": "https://api.example.com",
    "endpoints": [
        {{
            "path": "/api/endpoint",
            "method": "POST",
            "summary": "Brief description",
            "parameters": [
                {{
                    "name": "param_name",
                    "type": "string",
                    "required": true,
                    "location": "body"
                }}
            ],
            "auth_required": true,
            "responses": {{
                "200": "Success response description",
                "400": "Error response description"
            }}
        }}
    ]
}}

Return ONLY the JSON object, no markdown, no explanations."""

        try:
            response = self.invoke(user_prompt, system_prompt)
            result = self.parse_json_response(response)

            return result

        except Exception as e:
            logger.warning(f"Failed to parse chunk: {e}")
            return {"base_url": base_url, "endpoints": []}

    def _deduplicate_endpoints(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate endpoints based on path+method

        Args:
            endpoints: List of endpoint dicts

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []

        for endpoint in endpoints:
            key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

            if key not in seen:
                seen.add(key)
                unique.append(endpoint)

        if len(endpoints) != len(unique):
            logger.info(f"Deduplicated: {len(endpoints)} → {len(unique)} endpoints")

        return unique

    def _generate_api_summary(self, endpoints: List[Dict[str, Any]]) -> str:
        """
        Generate high-level API summary

        Args:
            endpoints: List of endpoints

        Returns:
            Summary string
        """
        if not endpoints:
            return "No endpoints found"

        method_counts = {}
        auth_count = 0

        for ep in endpoints:
            method = ep.get("method", "GET")
            method_counts[method] = method_counts.get(method, 0) + 1

            if ep.get("auth_required"):
                auth_count += 1

        summary_parts = [
            f"Total Endpoints: {len(endpoints)}",
            f"Methods: {', '.join(f'{m}={c}' for m, c in sorted(method_counts.items()))}",
            f"Authenticated: {auth_count}/{len(endpoints)}",
        ]

        return " | ".join(summary_parts)

    def identify_dependencies(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Identify dependencies between endpoints

        Args:
            endpoints: List of endpoints

        Returns:
            Dict mapping endpoint keys to list of dependency keys
        """
        logger.info("Identifying endpoint dependencies...")

        dependencies = {}

        # Common patterns for dependencies
        auth_endpoints = []
        create_endpoints = []

        for ep in endpoints:
            key = f"{ep['method']} {ep['path']}"

            # Identify authentication endpoints
            path_lower = ep['path'].lower()
            if any(term in path_lower for term in ['login', 'auth', 'signin', 'token']):
                auth_endpoints.append(key)

            # Identify creation endpoints
            if ep['method'] == 'POST' and any(term in path_lower for term in ['create', 'register', 'signup']):
                create_endpoints.append(key)

            # All auth-required endpoints depend on auth
            if ep.get('auth_required'):
                dependencies[key] = auth_endpoints.copy()

        logger.info(f"Found {len(auth_endpoints)} auth endpoints, {len(create_endpoints)} create endpoints")

        return dependencies

    def get_testing_order(
        self,
        endpoints: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Suggest optimal testing order based on dependencies

        Args:
            endpoints: List of endpoints

        Returns:
            Ordered list of endpoint keys
        """
        logger.info("Determining optimal testing order...")

        ordered = []

        # Group endpoints by priority
        auth_endpoints = []
        create_endpoints = []
        read_endpoints = []
        update_endpoints = []
        delete_endpoints = []

        for ep in endpoints:
            key = f"{ep['method']} {ep['path']}"
            path_lower = ep['path'].lower()
            method = ep['method']

            # Priority 1: Authentication
            if any(term in path_lower for term in ['login', 'auth', 'signin', 'token', 'signup', 'register']):
                auth_endpoints.append(key)

            # Priority 2: Create operations
            elif method == 'POST':
                create_endpoints.append(key)

            # Priority 3: Read operations
            elif method == 'GET':
                read_endpoints.append(key)

            # Priority 4: Update operations
            elif method in ['PUT', 'PATCH']:
                update_endpoints.append(key)

            # Priority 5: Delete operations
            elif method == 'DELETE':
                delete_endpoints.append(key)

        # Combine in logical order
        ordered = (
            auth_endpoints +
            create_endpoints +
            read_endpoints +
            update_endpoints +
            delete_endpoints
        )

        logger.info(
            f"Testing order: {len(auth_endpoints)} auth, "
            f"{len(create_endpoints)} create, {len(read_endpoints)} read, "
            f"{len(update_endpoints)} update, {len(delete_endpoints)} delete"
        )

        return ordered
