"""
Semantic Documentation Analyzer
Extracts natural language understanding from API documentation prose
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    logger = MockLogger()


@dataclass
class DocumentationContext:
    """Rich context extracted from API documentation"""
    endpoint: str
    method: str

    # Technical specifications
    parameters: List[Dict]
    request_schema: Dict
    response_schema: Dict

    # Natural language understanding (THIS IS THE KEY!)
    description: str              # What this endpoint does
    use_cases: List[str]          # When to use this API
    examples: List[Dict]          # Code examples with explanations
    best_practices: List[str]     # Recommended usage patterns
    common_errors: List[str]      # Known pitfalls and how to avoid them
    edge_cases: List[str]         # Special scenarios to handle
    business_rules: List[str]     # Implicit constraints from prose
    implementation_notes: List[str]  # How to implement correctly

    # Extracted constraints
    rate_limits: Optional[str]
    authentication_details: Optional[str]
    versioning_info: Optional[str]


class SemanticDocAnalyzer:
    """
    Analyzes API documentation to extract BOTH technical specs AND natural language understanding

    This is crucial because real API docs have:
    - Technical specs (OpenAPI): endpoints, schemas, parameters
    - Natural language prose: how to use it, why, when, examples, gotchas

    Traditional parsers only get the specs. We extract UNDERSTANDING.
    """

    def __init__(self, llm_client=None):
        """
        Initialize semantic analyzer

        Args:
            llm_client: LLM for semantic understanding (optional)
        """
        self.llm = llm_client

    def analyze_endpoint_documentation(
        self,
        raw_text: str,
        endpoint_path: str,
        method: str = "GET"
    ) -> DocumentationContext:
        """
        Extract rich context from endpoint documentation

        Args:
            raw_text: Full documentation text for this endpoint
            endpoint_path: API endpoint path
            method: HTTP method

        Returns:
            DocumentationContext with technical AND semantic understanding
        """
        logger.info(f"Analyzing documentation for {method} {endpoint_path}")

        # 1. Extract technical specifications (traditional parsing)
        parameters = self._extract_parameters(raw_text)
        request_schema = self._extract_request_schema(raw_text)
        response_schema = self._extract_response_schema(raw_text)

        # 2. Extract natural language explanations (NEW - THE KEY!)
        description = self._extract_description(raw_text)
        use_cases = self._extract_use_cases(raw_text)
        examples = self._extract_examples(raw_text)
        best_practices = self._extract_best_practices(raw_text)
        common_errors = self._extract_common_errors(raw_text)
        edge_cases = self._extract_edge_cases(raw_text)
        business_rules = self._extract_business_rules(raw_text)
        implementation_notes = self._extract_implementation_notes(raw_text)

        # 3. Extract operational details
        rate_limits = self._extract_rate_limits(raw_text)
        auth_details = self._extract_auth_details(raw_text)
        versioning = self._extract_versioning(raw_text)

        context = DocumentationContext(
            endpoint=endpoint_path,
            method=method,
            parameters=parameters,
            request_schema=request_schema,
            response_schema=response_schema,
            description=description,
            use_cases=use_cases,
            examples=examples,
            best_practices=best_practices,
            common_errors=common_errors,
            edge_cases=edge_cases,
            business_rules=business_rules,
            implementation_notes=implementation_notes,
            rate_limits=rate_limits,
            authentication_details=auth_details,
            versioning_info=versioning,
        )

        logger.info(
            f"Extracted: {len(examples)} examples, "
            f"{len(best_practices)} best practices, "
            f"{len(edge_cases)} edge cases"
        )

        return context

    def _extract_description(self, text: str) -> str:
        """Extract main description of what the endpoint does"""
        # Look for description sections
        patterns = [
            r"(?:Description|Overview|Summary)[:\s]*(.+?)(?:\n\n|\n[A-Z])",
            r"^([A-Z][^.!?]*[.!?])",  # First sentence
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if match:
                return match.group(1).strip()

        # Fallback: first paragraph
        paragraphs = text.split('\n\n')
        return paragraphs[0].strip() if paragraphs else ""

    def _extract_use_cases(self, text: str) -> List[str]:
        """
        Extract when/why to use this API

        Examples from real docs:
        - "Use this endpoint when you need to..."
        - "This is useful for..."
        - "Common use cases include..."
        """
        use_cases = []

        # Pattern 1: Explicit use case sections
        use_case_match = re.search(
            r"(?:Use [Cc]ases?|When to [Uu]se|Common [Ss]cenarios?)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.MULTILINE | re.DOTALL
        )
        if use_case_match:
            section = use_case_match.group(1)
            # Split by bullets or newlines
            cases = re.split(r'\n[-*•]\s*|\n\d+\.\s*', section)
            use_cases.extend([c.strip() for c in cases if c.strip()])

        # Pattern 2: "Use this when..." sentences
        when_matches = re.findall(
            r"Use this (?:endpoint|API|method) when (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        use_cases.extend(when_matches)

        # Pattern 3: "This is useful for..." sentences
        useful_matches = re.findall(
            r"(?:This is )?useful for (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        use_cases.extend(useful_matches)

        return [uc.strip() for uc in use_cases if len(uc.strip()) > 10]

    def _extract_examples(self, text: str) -> List[Dict]:
        """
        Extract code examples with their explanations

        Real docs have examples like:
        ```
        // Create a new user
        POST /users
        {
          "name": "John Doe",
          "email": "john@example.com"
        }

        // Response
        {
          "id": 123,
          "name": "John Doe",
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```

        We want to extract BOTH the code AND the explanation!
        """
        examples = []

        # Pattern: Code blocks with optional explanations
        code_blocks = re.finditer(
            r"(?://\s*(.+?)\n)?```(\w+)?\n(.+?)\n```",
            text,
            re.DOTALL
        )

        for match in code_blocks:
            explanation = match.group(1) if match.group(1) else ""
            language = match.group(2) if match.group(2) else "unknown"
            code = match.group(3).strip()

            examples.append({
                'explanation': explanation.strip(),
                'language': language,
                'code': code,
                'type': self._classify_example(code)
            })

        # Pattern: cURL examples
        curl_examples = re.finditer(
            r"(?:Example|cURL)[:\s]*\n?(curl\s+.+?)(?:\n\n|\n[A-Z])",
            text,
            re.MULTILINE | re.DOTALL
        )

        for match in curl_examples:
            examples.append({
                'explanation': 'cURL example',
                'language': 'bash',
                'code': match.group(1).strip(),
                'type': 'request'
            })

        return examples

    def _classify_example(self, code: str) -> str:
        """Classify what type of example this is"""
        code_lower = code.lower()

        if any(method in code_lower for method in ['post', 'put', 'patch']):
            return 'request_with_body'
        elif 'get' in code_lower or 'delete' in code_lower:
            return 'request_simple'
        elif '"id"' in code_lower or '"status"' in code_lower:
            return 'response'
        elif 'error' in code_lower or 'exception' in code_lower:
            return 'error_example'
        else:
            return 'unknown'

    def _extract_best_practices(self, text: str) -> List[str]:
        """
        Extract recommended usage patterns

        Examples:
        - "Always include X header"
        - "It's recommended to..."
        - "Best practice is to..."
        """
        practices = []

        # Pattern 1: Best practice sections
        bp_match = re.search(
            r"(?:Best [Pp]ractices?|Recommendations?|Guidelines?)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.MULTILINE | re.DOTALL
        )
        if bp_match:
            section = bp_match.group(1)
            items = re.split(r'\n[-*•]\s*|\n\d+\.\s*', section)
            practices.extend([i.strip() for i in items if i.strip()])

        # Pattern 2: "Always..." sentences
        always_matches = re.findall(
            r"Always (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        practices.extend([f"Always {m}" for m in always_matches])

        # Pattern 3: "It's recommended..." sentences
        rec_matches = re.findall(
            r"(?:It's |It is )?recommended to (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        practices.extend([f"Recommended to {m}" for m in rec_matches])

        # Pattern 4: "Should..." sentences
        should_matches = re.findall(
            r"You should (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        practices.extend([f"Should {m}" for m in should_matches])

        return [p.strip() for p in practices if len(p.strip()) > 10]

    def _extract_common_errors(self, text: str) -> List[str]:
        """
        Extract known pitfalls and common mistakes

        Examples:
        - "Common error: forgetting to..."
        - "Note: this will fail if..."
        - "⚠️ Warning: ..."
        """
        errors = []

        # Pattern 1: Error sections
        error_match = re.search(
            r"(?:Common [Ee]rrors?|Pitfalls?|Troubleshooting|Known [Ii]ssues?)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.MULTILINE | re.DOTALL
        )
        if error_match:
            section = error_match.group(1)
            items = re.split(r'\n[-*•]\s*|\n\d+\.\s*', section)
            errors.extend([i.strip() for i in items if i.strip()])

        # Pattern 2: Warning markers
        warnings = re.findall(
            r"(?:⚠️|Warning|Caution|Note)[:\s]*(.+?)[.!]",
            text,
            re.MULTILINE
        )
        errors.extend(warnings)

        # Pattern 3: "Will fail if..." sentences
        fail_matches = re.findall(
            r"(?:will|may) fail (?:if|when|unless) (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        errors.extend([f"Fails if {m}" for m in fail_matches])

        return [e.strip() for e in errors if len(e.strip()) > 10]

    def _extract_edge_cases(self, text: str) -> List[str]:
        """
        Extract special scenarios to handle

        Examples:
        - "When the user is new..."
        - "If the resource doesn't exist..."
        - "For pagination beyond 100 items..."
        """
        edge_cases = []

        # Pattern 1: Conditional sentences
        if_matches = re.findall(
            r"(?:If|When|For) (.+?), (?:then |you )?(.+?)[.!]",
            text,
            re.IGNORECASE
        )
        edge_cases.extend([f"If {condition}: {action}" for condition, action in if_matches])

        # Pattern 2: Special case sections
        special_match = re.search(
            r"(?:Special [Cc]ases?|Edge [Cc]ases?|Exceptions?)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.MULTILINE | re.DOTALL
        )
        if special_match:
            section = special_match.group(1)
            items = re.split(r'\n[-*•]\s*|\n\d+\.\s*', section)
            edge_cases.extend([i.strip() for i in items if i.strip()])

        return [ec.strip() for ec in edge_cases if len(ec.strip()) > 15]

    def _extract_business_rules(self, text: str) -> List[str]:
        """
        Extract implicit business logic constraints from prose

        Examples:
        - "Users must be verified before..."
        - "Only admins can..."
        - "Maximum 10 items per request"
        """
        rules = []

        # Pattern 1: "Must..." constraints
        must_matches = re.findall(
            r"(?:must|required to) (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        rules.extend([f"Must {m}" for m in must_matches])

        # Pattern 2: "Cannot..." prohibitions
        cannot_matches = re.findall(
            r"(?:cannot|can't|may not|must not) (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        rules.extend([f"Cannot {m}" for m in cannot_matches])

        # Pattern 3: "Only..." restrictions
        only_matches = re.findall(
            r"Only (.+?) can (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        rules.extend([f"Only {who} can {what}" for who, what in only_matches])

        # Pattern 4: Numeric limits
        limit_matches = re.findall(
            r"(?:maximum|max|minimum|min|limit of) (\d+) (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        rules.extend([f"Limit: {num} {desc}" for num, desc in limit_matches])

        return [r.strip() for r in rules if len(r.strip()) > 10]

    def _extract_implementation_notes(self, text: str) -> List[str]:
        """
        Extract how-to implementation guidance

        Examples:
        - "To implement this, first..."
        - "The typical flow is..."
        - "Step 1: ..., Step 2: ..."
        """
        notes = []

        # Pattern 1: Implementation sections
        impl_match = re.search(
            r"(?:Implementation|How to [Uu]se|Getting [Ss]tarted|Tutorial)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.MULTILINE | re.DOTALL
        )
        if impl_match:
            section = impl_match.group(1)
            items = re.split(r'\n[-*•]\s*|\n(?:Step )?\d+[.:]\s*', section)
            notes.extend([i.strip() for i in items if i.strip()])

        # Pattern 2: Ordered steps
        steps = re.findall(
            r"(?:First|Then|Next|Finally),? (.+?)[.!]",
            text,
            re.IGNORECASE
        )
        notes.extend(steps)

        return [n.strip() for n in notes if len(n.strip()) > 15]

    def _extract_parameters(self, text: str) -> List[Dict]:
        """Extract parameters from technical specs (traditional parsing)"""
        # This would parse OpenAPI specs, JSON schemas, etc.
        # Placeholder for now
        return []

    def _extract_request_schema(self, text: str) -> Dict:
        """Extract request schema (traditional parsing)"""
        return {}

    def _extract_response_schema(self, text: str) -> Dict:
        """Extract response schema (traditional parsing)"""
        return {}

    def _extract_rate_limits(self, text: str) -> Optional[str]:
        """Extract rate limiting information"""
        rate_match = re.search(
            r"(?:rate limit|requests? per|calls? per)[:\s]*(.+?)[.!]",
            text,
            re.IGNORECASE
        )
        return rate_match.group(0).strip() if rate_match else None

    def _extract_auth_details(self, text: str) -> Optional[str]:
        """Extract authentication details"""
        auth_match = re.search(
            r"(?:authentication|authorization|auth)[:\s]*(.+?)(?:\n\n|\n[A-Z#])",
            text,
            re.IGNORECASE | re.DOTALL
        )
        return auth_match.group(1).strip() if auth_match else None

    def _extract_versioning(self, text: str) -> Optional[str]:
        """Extract API versioning information"""
        version_match = re.search(
            r"(?:version|v)\s*(\d+(?:\.\d+)*)",
            text,
            re.IGNORECASE
        )
        return version_match.group(0).strip() if version_match else None
