"""
Enhanced Document Parser with Semantic Analysis
Automatically extracts semantic understanding from API documentation
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

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

from src.parsers.document_parser import DocumentParser
from src.analysis.semantic_doc_analyzer import SemanticDocAnalyzer, DocumentationContext


class EnhancedDocumentParser:
    """
    Document parser that combines traditional parsing with semantic analysis

    Flow:
    1. Parse document (PDF/JSON/YAML) → raw text + structure
    2. Validate if it's API documentation
    3. Extract endpoints from structure
    4. For each endpoint: Run semantic analysis on relevant text
    5. Return parsed data + semantic contexts
    """

    def __init__(self, enable_semantic_analysis: bool = True):
        """
        Initialize enhanced parser

        Args:
            enable_semantic_analysis: Whether to run semantic analysis (default True)
        """
        self.parser = DocumentParser()
        self.semantic_analyzer = SemanticDocAnalyzer() if enable_semantic_analysis else None
        self.enable_semantic_analysis = enable_semantic_analysis

        logger.info(
            f"EnhancedDocumentParser initialized "
            f"(semantic_analysis={'ON' if enable_semantic_analysis else 'OFF'})"
        )

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse document with semantic analysis

        Args:
            file_path: Path to document file

        Returns:
            Dict with:
                - raw_text: Full extracted text
                - metadata: Document metadata
                - doc_type: Document type
                - structured_data: Parsed structure
                - endpoints: List of discovered endpoints (if API doc)
                - semantic_contexts: Dict[endpoint_key, DocumentationContext]
        """
        # Step 1: Traditional parsing
        logger.info(f"📄 Parsing document: {file_path.name}")
        parsed = self.parser.parse(file_path)

        # Step 2: Detect if this is API documentation
        is_api_doc = self.parser.validate_api_doc(parsed)

        if not is_api_doc:
            logger.warning("Document does not appear to be API documentation")
            return {
                **parsed,
                'is_api_doc': False,
                'endpoints': [],
                'semantic_contexts': {}
            }

        logger.info("✅ Detected API documentation")

        # Step 3: Extract endpoints
        base_url = self.parser.extract_base_url(parsed)
        endpoints = self._extract_endpoints_with_text(parsed)

        logger.info(f"📍 Found {len(endpoints)} endpoints")

        # Step 4: Semantic analysis for each endpoint
        semantic_contexts = {}

        if self.enable_semantic_analysis and endpoints:
            logger.info("🧠 Running semantic analysis on endpoints...")

            for endpoint in endpoints:
                endpoint_key = f"{endpoint['method']} {endpoint['path']}"

                # Get relevant text for this endpoint
                endpoint_text = self._get_endpoint_documentation(
                    parsed['raw_text'],
                    endpoint
                )

                # Analyze semantically
                try:
                    context = self.semantic_analyzer.analyze_endpoint_documentation(
                        raw_text=endpoint_text,
                        endpoint_path=endpoint['path'],
                        method=endpoint['method']
                    )

                    semantic_contexts[endpoint_key] = context

                    logger.info(
                        f"  ✅ {endpoint_key}: "
                        f"{len(context.use_cases)} use cases, "
                        f"{len(context.examples)} examples, "
                        f"{len(context.edge_cases)} edge cases"
                    )

                except Exception as e:
                    logger.warning(f"  ⚠️  Failed to analyze {endpoint_key}: {e}")
                    semantic_contexts[endpoint_key] = None

        # Step 5: Return enhanced data
        return {
            **parsed,
            'is_api_doc': True,
            'base_url': base_url,
            'endpoints': endpoints,
            'semantic_contexts': semantic_contexts,
            'semantic_summary': self._create_semantic_summary(semantic_contexts)
        }

    def _extract_endpoints_with_text(self, parsed: Dict[str, Any]) -> List[Dict]:
        """
        Extract endpoints from parsed document

        Args:
            parsed: Parsed document data

        Returns:
            List of endpoint dicts with paths, methods, and text sections
        """
        endpoints = []

        # Method 1: Extract from structured data (JSON/YAML)
        if parsed.get('structured_data'):
            structured_endpoints = self._extract_from_structured(
                parsed['structured_data']
            )
            endpoints.extend(structured_endpoints)

        # Method 2: Extract from raw text (PDF, plain text)
        if parsed.get('raw_text') and not endpoints:
            text_endpoints = self._extract_from_text(parsed['raw_text'])
            endpoints.extend(text_endpoints)

        return endpoints

    def _extract_from_structured(self, data: Dict) -> List[Dict]:
        """Extract endpoints from structured data (OpenAPI, etc.)"""
        endpoints = []

        # OpenAPI 3.0 format
        if 'paths' in data:
            for path, methods in data['paths'].items():
                if isinstance(methods, dict):
                    for method, spec in methods.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                            endpoints.append({
                                'path': path,
                                'method': method.upper(),
                                'summary': spec.get('summary', ''),
                                'description': spec.get('description', ''),
                                'parameters': spec.get('parameters', []),
                                'spec': spec
                            })

        # Simple JSON format
        elif 'endpoints' in data:
            for ep in data['endpoints']:
                endpoints.append({
                    'path': ep.get('path', ''),
                    'method': ep.get('method', 'GET').upper(),
                    'summary': ep.get('summary', ''),
                    'description': ep.get('description', ''),
                    'parameters': ep.get('parameters', [])
                })

        return endpoints

    def _extract_from_text(self, text: str) -> List[Dict]:
        """Extract endpoints from raw text using pattern matching"""
        import re

        endpoints = []

        # Pattern: HTTP method followed by path
        # Examples: "POST /api/users", "GET /users/{id}"
        pattern = r'\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s\n]+)'

        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)

            # Avoid duplicates
            if not any(ep['path'] == path and ep['method'] == method for ep in endpoints):
                endpoints.append({
                    'path': path,
                    'method': method,
                    'summary': '',
                    'description': '',
                    'parameters': []
                })

        return endpoints

    def _get_endpoint_documentation(
        self,
        full_text: str,
        endpoint: Dict
    ) -> str:
        """
        Extract the relevant documentation section for an endpoint

        Args:
            full_text: Full document text
            endpoint: Endpoint dict with path and method

        Returns:
            Text section relevant to this endpoint
        """
        import re

        method = endpoint['method']
        path = endpoint['path']

        # Look for section headers mentioning this endpoint
        # Examples: "## POST /users", "### Create User (POST /users)"

        # Pattern 1: Exact match in headers
        pattern1 = rf'(?:^|\n)(#{1,6})\s+.*{method}.*{re.escape(path)}.*\n(.+?)(?=\n#{1,6}\s+|\Z)'
        match1 = re.search(pattern1, full_text, re.DOTALL | re.IGNORECASE)

        if match1:
            return match1.group(2).strip()

        # Pattern 2: Find section by path, then look for method
        pattern2 = rf'(?:^|\n)(#{1,6})\s+.*{re.escape(path)}.*\n(.+?)(?=\n#{1,6}\s+|\Z)'
        match2 = re.search(pattern2, full_text, re.DOTALL)

        if match2:
            section = match2.group(2)
            # Check if method is mentioned in this section
            if method.lower() in section.lower():
                return section.strip()

        # Pattern 3: Search around the first mention of "METHOD /path"
        pattern3 = rf'({method}\s+{re.escape(path)})'
        match3 = re.search(pattern3, full_text, re.IGNORECASE)

        if match3:
            start = max(0, match3.start() - 500)  # 500 chars before
            end = min(len(full_text), match3.end() + 2000)  # 2000 chars after
            return full_text[start:end]

        # Fallback: Return full text (semantic analyzer will extract what it can)
        logger.debug(f"Could not isolate section for {method} {path}, using full text")
        return full_text

    def _create_semantic_summary(
        self,
        semantic_contexts: Dict[str, DocumentationContext]
    ) -> Dict[str, Any]:
        """
        Create summary of semantic analysis results

        Args:
            semantic_contexts: Dict of endpoint contexts

        Returns:
            Summary dict with aggregate statistics
        """
        if not semantic_contexts:
            return {
                'total_endpoints': 0,
                'endpoints_analyzed': 0,
                'total_use_cases': 0,
                'total_examples': 0,
                'total_best_practices': 0,
                'total_common_errors': 0,
                'total_edge_cases': 0,
                'total_business_rules': 0,
            }

        # Filter out None values
        valid_contexts = [c for c in semantic_contexts.values() if c is not None]

        return {
            'total_endpoints': len(semantic_contexts),
            'endpoints_analyzed': len(valid_contexts),
            'total_use_cases': sum(len(c.use_cases) for c in valid_contexts),
            'total_examples': sum(len(c.examples) for c in valid_contexts),
            'total_best_practices': sum(len(c.best_practices) for c in valid_contexts),
            'total_common_errors': sum(len(c.common_errors) for c in valid_contexts),
            'total_edge_cases': sum(len(c.edge_cases) for c in valid_contexts),
            'total_business_rules': sum(len(c.business_rules) for c in valid_contexts),
            'avg_use_cases_per_endpoint': sum(len(c.use_cases) for c in valid_contexts) / len(valid_contexts) if valid_contexts else 0,
            'avg_examples_per_endpoint': sum(len(c.examples) for c in valid_contexts) / len(valid_contexts) if valid_contexts else 0,
            'coverage_quality': self._assess_coverage_quality(valid_contexts)
        }

    def _assess_coverage_quality(self, contexts: List[DocumentationContext]) -> str:
        """
        Assess the quality of semantic coverage

        Args:
            contexts: List of valid documentation contexts

        Returns:
            Quality assessment: EXCELLENT, GOOD, FAIR, POOR
        """
        if not contexts:
            return "NONE"

        # Calculate coverage score
        total_elements = 0
        for context in contexts:
            total_elements += len(context.use_cases)
            total_elements += len(context.examples) * 2  # Examples are valuable
            total_elements += len(context.best_practices)
            total_elements += len(context.common_errors)
            total_elements += len(context.edge_cases)
            total_elements += len(context.business_rules)

        avg_elements = total_elements / len(contexts)

        # Assess quality
        if avg_elements >= 15:
            return "EXCELLENT"  # Comprehensive documentation
        elif avg_elements >= 8:
            return "GOOD"       # Well documented
        elif avg_elements >= 3:
            return "FAIR"       # Basic documentation
        else:
            return "POOR"       # Minimal documentation
