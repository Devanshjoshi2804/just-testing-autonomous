# Phase 8: Universal Document Analysis & Intelligent Test Generation

## Objective
Build on Phase 7.3 (Parallel Execution) to create an AI-powered system that can:
1. **Ingest any API documentation** (OpenAPI, Postman, text, PDF)
2. **Understand the API semantically** using LLM
3. **Generate comprehensive test suites automatically**
4. **Achieve 100% coverage** without manual intervention

---

## Current State (After Phase 7.3)

✅ **Completed:**
- Database persistence layer (Phase 7.1)
- Redis caching layer (Phase 7.2)
- Parallel execution system (Phase 7.3)
  - Worker pool (10 concurrent workers)
  - Priority task queue
  - Result aggregation
  - Rate limiting & backpressure

✅ **Existing Capabilities:**
- OpenAPI/Swagger parsing (`src/parsers/document_parser.py`)
- Endpoint analysis (`src/agents/endpoint_analyzer.py`)
- Test generation (`src/agents/enhanced_test_generator.py`)
- Constraint extraction (`src/analysis/constraint_extractor.py`)

📊 **Current Test Coverage:** ~1600 lines of test code

---

## Phase 8 Architecture

### Phase 8.1: Multi-Format Document Ingestion (Week 1)

**Goal:** Accept ANY documentation format and normalize to unified spec

#### New Components:

**1. Universal Document Parser**
```
src/ingestion/
├── __init__.py
├── universal_parser.py          # Main entry point
├── format_detector.py            # Auto-detect doc format
├── parsers/
│   ├── openapi_parser.py         # Enhanced OpenAPI parser
│   ├── postman_parser.py         # Postman collection parser
│   ├── text_parser.py            # LLM-powered text extraction
│   └── pdf_parser.py             # PDF extraction
└── models/
    └── unified_spec.py           # Unified API specification model
```

**2. Implementation Details:**

```python
# src/ingestion/universal_parser.py
from typing import Union, BinaryIO
from src.ingestion.format_detector import FormatDetector
from src.ingestion.models.unified_spec import UnifiedAPISpec

class UniversalDocumentParser:
    """
    Accepts any API documentation format and converts to unified spec
    """

    def __init__(self):
        self.format_detector = FormatDetector()
        self.parsers = {
            'openapi_json': OpenAPIParser(),
            'openapi_yaml': OpenAPIParser(),
            'postman': PostmanParser(),
            'text': LLMTextParser(),
            'pdf': PDFParser(),
            'markdown': MarkdownParser()
        }

    async def parse(
        self,
        document: Union[str, bytes, BinaryIO],
        filename: str = None
    ) -> UnifiedAPISpec:
        """
        Auto-detect format and parse to unified specification

        Args:
            document: Raw document content
            filename: Optional filename for format hints

        Returns:
            UnifiedAPISpec with all endpoints, schemas, auth, etc.
        """
        # Detect format
        format_type = self.format_detector.detect(document, filename)

        # Get appropriate parser
        parser = self.parsers.get(format_type)
        if not parser:
            raise ValueError(f"Unsupported format: {format_type}")

        # Parse to unified spec
        spec = await parser.parse(document)

        # Validate completeness
        await self._validate_spec(spec)

        return spec

    async def _validate_spec(self, spec: UnifiedAPISpec):
        """Ensure spec has all required information"""
        if not spec.endpoints:
            raise ValueError("No endpoints found in documentation")

        if not spec.base_url and not spec.servers:
            raise ValueError("No base URL or servers defined")
```

**3. LLM-Powered Text Parser:**

```python
# src/ingestion/parsers/text_parser.py
from anthropic import Anthropic

class LLMTextParser:
    """
    Use Claude to extract API specification from unstructured text
    """

    def __init__(self):
        self.client = Anthropic()

    async def parse(self, text: str) -> UnifiedAPISpec:
        """
        Extract structured API spec from text using LLM
        """
        prompt = f"""
        You are an API documentation analyzer. Extract ALL API endpoint information from this documentation.

        For each endpoint, extract:
        - HTTP method (GET, POST, PUT, DELETE, etc.)
        - Path (e.g., /api/users/{{id}})
        - Description
        - Parameters (path, query, body)
        - Request schema
        - Response schema
        - Authentication requirements
        - Example requests/responses
        - Error responses
        - Rate limits
        - Any constraints or validation rules

        Documentation:
        {text}

        Return a complete JSON structure with all endpoints.
        """

        response = await self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse LLM response into structured spec
        spec_data = self._parse_llm_response(response.content[0].text)

        return UnifiedAPISpec.from_dict(spec_data)
```

**4. Unified Specification Model:**

```python
# src/ingestion/models/unified_spec.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class EndpointSpec(BaseModel):
    """Single endpoint specification"""
    method: str
    path: str
    description: Optional[str]
    parameters: List[ParameterSpec] = []
    request_body: Optional[SchemaSpec]
    responses: Dict[int, ResponseSpec]
    auth_required: bool = False
    auth_schemes: List[str] = []
    tags: List[str] = []
    rate_limit: Optional[RateLimitSpec]
    examples: List[ExampleSpec] = []

class UnifiedAPISpec(BaseModel):
    """
    Unified API specification supporting all input formats
    """
    title: str
    version: str
    description: Optional[str]
    base_url: Optional[str]
    servers: List[ServerSpec] = []
    endpoints: List[EndpointSpec]
    schemas: Dict[str, SchemaSpec] = {}
    auth_schemes: Dict[str, AuthSchemeSpec] = {}
    metadata: Dict[str, Any] = {}

    def get_all_endpoints(self) -> List[EndpointSpec]:
        """Get all endpoints"""
        return self.endpoints

    def get_endpoints_by_tag(self, tag: str) -> List[EndpointSpec]:
        """Filter endpoints by tag"""
        return [e for e in self.endpoints if tag in e.tags]

    def to_openapi(self) -> Dict:
        """Convert to OpenAPI 3.0 format"""
        # For standardization and tooling compatibility
        pass
```

---

### Phase 8.2: Semantic API Understanding (Week 2)

**Goal:** Use LLM to deeply understand API semantics, business logic, dependencies

#### New Components:

**1. Semantic Analyzer**
```
src/intelligence/
├── __init__.py
├── semantic_analyzer.py          # Main LLM-powered analyzer
├── dependency_detector.py        # Find endpoint dependencies
├── auth_flow_analyzer.py         # Understand auth requirements
├── business_rule_extractor.py    # Extract business logic
└── models/
    └── semantic_model.py         # Semantic understanding model
```

**2. Implementation:**

```python
# src/intelligence/semantic_analyzer.py
from anthropic import Anthropic
from src.ingestion.models.unified_spec import UnifiedAPISpec
from src.intelligence.models.semantic_model import SemanticModel

class SemanticAPIAnalyzer:
    """
    Deeply understand API using LLM
    """

    def __init__(self):
        self.client = Anthropic()
        self.dependency_detector = DependencyDetector()
        self.auth_analyzer = AuthFlowAnalyzer()
        self.business_rule_extractor = BusinessRuleExtractor()

    async def analyze(self, spec: UnifiedAPISpec) -> SemanticModel:
        """
        Perform deep semantic analysis of API
        """
        # Parallel analysis
        dependencies, auth_flows, business_rules, constraints = await asyncio.gather(
            self.dependency_detector.detect(spec),
            self.auth_analyzer.analyze(spec),
            self.business_rule_extractor.extract(spec),
            self._extract_implicit_constraints(spec)
        )

        return SemanticModel(
            dependencies=dependencies,
            auth_flows=auth_flows,
            business_rules=business_rules,
            constraints=constraints,
            test_flows=self._identify_test_flows(dependencies)
        )

    async def _extract_implicit_constraints(self, spec: UnifiedAPISpec) -> List[Constraint]:
        """
        Use LLM to find constraints not explicitly stated

        Example: "Users can only edit their own posts" -> OwnershipConstraint
        """
        prompt = f"""
        Analyze this API specification and identify ALL validation rules,
        business constraints, and logical requirements that must be tested.

        Look for:
        - Required field validations
        - Data format requirements
        - Relationship constraints (e.g., foreign keys)
        - Authorization rules (who can do what)
        - State requirements (e.g., must verify email before posting)
        - Temporal constraints (e.g., cannot delete within 24 hours)
        - Business logic rules

        API Spec:
        {spec.model_dump_json(indent=2)}

        Return structured constraints.
        """

        response = await self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse and structure constraints
        return self._parse_constraints(response.content[0].text)
```

**3. Dependency Detection:**

```python
# src/intelligence/dependency_detector.py
class DependencyDetector:
    """
    Detect dependencies between endpoints
    """

    async def detect(self, spec: UnifiedAPISpec) -> DependencyGraph:
        """
        Identify which endpoints depend on others

        Examples:
        - POST /users/{id}/posts depends on POST /users
        - DELETE /users/{id} should come after testing other user operations
        - PUT /posts/{id}/publish depends on POST /posts/{id}
        """
        graph = DependencyGraph()

        for endpoint in spec.endpoints:
            # Analyze path structure
            if self._is_nested_resource(endpoint.path):
                parent_endpoint = self._find_parent_resource(endpoint, spec)
                if parent_endpoint:
                    graph.add_dependency(endpoint, parent_endpoint)

            # Analyze request body references
            if endpoint.request_body:
                for ref in self._extract_schema_refs(endpoint.request_body):
                    creator_endpoint = self._find_creator_endpoint(ref, spec)
                    if creator_endpoint:
                        graph.add_dependency(endpoint, creator_endpoint)

            # Use LLM for complex dependencies
            implicit_deps = await self._detect_implicit_dependencies(endpoint, spec)
            for dep in implicit_deps:
                graph.add_dependency(endpoint, dep)

        return graph

    async def _detect_implicit_dependencies(
        self,
        endpoint: EndpointSpec,
        spec: UnifiedAPISpec
    ) -> List[EndpointSpec]:
        """
        Use LLM to find non-obvious dependencies

        Example: "This endpoint requires user to be premium member"
        -> Depends on endpoint that upgrades user to premium
        """
        # LLM analysis here
        pass
```

---

### Phase 8.3: Intelligent Test Generation (Week 3)

**Goal:** Generate comprehensive test suites automatically covering all scenarios

#### Enhanced Test Generator:

```python
# src/generation/intelligent_test_generator.py
from src.intelligence.models.semantic_model import SemanticModel
from src.ingestion.models.unified_spec import UnifiedAPISpec

class IntelligentTestGenerator:
    """
    Generate comprehensive test suites using semantic understanding
    """

    def __init__(self):
        self.positive_generator = PositiveTestGenerator()
        self.negative_generator = NegativeTestGenerator()
        self.security_generator = SecurityTestGenerator()
        self.edge_case_generator = EdgeCaseGenerator()
        self.flow_generator = IntegrationFlowGenerator()

    async def generate_complete_suite(
        self,
        spec: UnifiedAPISpec,
        semantic_model: SemanticModel
    ) -> ComprehensiveTestSuite:
        """
        Generate 100% coverage test suite
        """
        test_suite = ComprehensiveTestSuite()

        # 1. Generate tests for each endpoint
        for endpoint in spec.endpoints:
            # Positive tests
            test_suite.add(
                await self.positive_generator.generate(endpoint, semantic_model)
            )

            # Negative tests (all possible failures)
            test_suite.add(
                await self.negative_generator.generate(endpoint, semantic_model)
            )

            # Security tests
            test_suite.add(
                await self.security_generator.generate(endpoint, semantic_model)
            )

            # Edge cases
            test_suite.add(
                await self.edge_case_generator.generate(endpoint, semantic_model)
            )

        # 2. Generate integration tests (test flows)
        for flow in semantic_model.test_flows:
            test_suite.add(
                await self.flow_generator.generate(flow)
            )

        # 3. Generate security suite (OWASP API Top 10)
        test_suite.add(
            await self._generate_security_suite(spec, semantic_model)
        )

        # 4. Generate performance tests
        test_suite.add(
            await self._generate_performance_suite(spec)
        )

        return test_suite

    async def _generate_security_suite(
        self,
        spec: UnifiedAPISpec,
        semantic_model: SemanticModel
    ) -> SecurityTestSuite:
        """
        Generate tests for OWASP API Security Top 10
        """
        tests = SecurityTestSuite()

        # API1: Broken Object Level Authorization
        tests.add(await self._test_broken_object_auth(spec))

        # API2: Broken Authentication
        tests.add(await self._test_broken_auth(spec))

        # API3: Broken Object Property Level Authorization
        tests.add(await self._test_property_auth(spec))

        # API4: Unrestricted Resource Consumption
        tests.add(await self._test_rate_limiting(spec))

        # API5: Broken Function Level Authorization
        tests.add(await self._test_function_auth(spec))

        # API6: Unrestricted Access to Sensitive Business Flows
        tests.add(await self._test_business_flow_auth(spec))

        # API7: Server Side Request Forgery
        tests.add(await self._test_ssrf(spec))

        # API8: Security Misconfiguration
        tests.add(await self._test_security_config(spec))

        # API9: Improper Inventory Management
        tests.add(await self._test_inventory(spec))

        # API10: Unsafe Consumption of APIs
        tests.add(await self._test_unsafe_consumption(spec))

        return tests
```

---

### Phase 8.4: Smart Test Data Generation (Week 4)

**Goal:** Generate realistic, valid, and invalid test data automatically

#### Implementation:

```python
# src/generation/smart_data_generator.py
class SmartDataGenerator:
    """
    Generate intelligent test data based on schema and context
    """

    def __init__(self):
        self.faker = Faker()
        self.llm_client = Anthropic()

    async def generate_valid_data(
        self,
        schema: SchemaSpec,
        context: Dict
    ) -> Any:
        """
        Generate valid data that passes all constraints
        """
        if schema.type == 'object':
            return await self._generate_object(schema, context)
        elif schema.type == 'array':
            return await self._generate_array(schema, context)
        else:
            return await self._generate_primitive(schema, context)

    async def generate_invalid_data_suite(
        self,
        schema: SchemaSpec
    ) -> List[InvalidDataCase]:
        """
        Generate ALL possible invalid variations
        """
        invalid_cases = []

        # Type violations
        invalid_cases.extend(self._generate_type_violations(schema))

        # Constraint violations
        if schema.min_length:
            invalid_cases.append(InvalidDataCase(
                type='constraint_violation',
                field=schema.name,
                value='x' * (schema.min_length - 1),
                expected_error='Value too short'
            ))

        if schema.max_length:
            invalid_cases.append(InvalidDataCase(
                type='constraint_violation',
                field=schema.name,
                value='x' * (schema.max_length + 1),
                expected_error='Value too long'
            ))

        # Format violations
        if schema.format == 'email':
            invalid_cases.extend([
                InvalidDataCase(value='not-an-email', expected_error='Invalid email'),
                InvalidDataCase(value='@nodomain.com', expected_error='Invalid email'),
                InvalidDataCase(value='noat.com', expected_error='Invalid email'),
            ])

        # Pattern violations
        if schema.pattern:
            invalid_cases.extend(
                await self._generate_pattern_violations(schema.pattern)
            )

        # Enum violations
        if schema.enum:
            invalid_cases.append(InvalidDataCase(
                value='not_in_enum',
                expected_error=f'Must be one of {schema.enum}'
            ))

        # Boundary cases
        invalid_cases.extend(self._generate_boundary_violations(schema))

        # Injection attempts (security)
        invalid_cases.extend(self._generate_injection_tests(schema))

        return invalid_cases

    async def _generate_realistic_data(
        self,
        field_name: str,
        schema: SchemaSpec,
        context: Dict
    ) -> Any:
        """
        Use LLM to generate contextually appropriate data

        Example: For a "company_name" field, generate realistic company names
        """
        prompt = f"""
        Generate realistic test data for this field:

        Field: {field_name}
        Type: {schema.type}
        Description: {schema.description}
        Constraints: {schema.constraints}
        Context: {context}

        Generate 5 diverse, realistic values.
        """

        # LLM generates contextually appropriate data
        return await self._llm_generate_data(prompt)
```

---

## Integration with Existing System

### Update API Routes

```python
# src/api/routes/intelligent_testing.py
from fastapi import APIRouter, UploadFile, File
from src.ingestion.universal_parser import UniversalDocumentParser
from src.intelligence.semantic_analyzer import SemanticAPIAnalyzer
from src.generation.intelligent_test_generator import IntelligentTestGenerator
from src.execution import ParallelTestExecutor

router = APIRouter(prefix="/api/v1/intelligent", tags=["intelligent"])

@router.post("/analyze-and-test")
async def analyze_and_test_api(
    document: UploadFile = File(...),
    auto_execute: bool = True
):
    """
    Upload ANY API documentation and get comprehensive test results

    Steps:
    1. Parse document (auto-detect format)
    2. Semantic analysis (understand API deeply)
    3. Generate comprehensive test suite
    4. Execute tests in parallel
    5. Return results with insights
    """
    # 1. Parse document
    content = await document.read()
    parser = UniversalDocumentParser()
    spec = await parser.parse(content, document.filename)

    # 2. Semantic analysis
    analyzer = SemanticAPIAnalyzer()
    semantic_model = await analyzer.analyze(spec)

    # 3. Generate tests
    generator = IntelligentTestGenerator()
    test_suite = await generator.generate_complete_suite(spec, semantic_model)

    # 4. Execute if requested
    if auto_execute:
        executor = ParallelTestExecutor(num_workers=20)
        results = await executor.execute_tests(test_suite.to_executable())

        return {
            "success": True,
            "spec_summary": spec.get_summary(),
            "semantic_insights": semantic_model.get_insights(),
            "test_suite": test_suite.get_summary(),
            "execution_results": results
        }
    else:
        return {
            "success": True,
            "spec_summary": spec.get_summary(),
            "semantic_insights": semantic_model.get_insights(),
            "test_suite": test_suite.get_summary(),
            "tests_generated": len(test_suite.tests),
            "estimated_execution_time": test_suite.estimate_duration()
        }
```

---

## Success Metrics

### Coverage Targets:
- ✅ **Endpoint Coverage**: 100% of documented endpoints
- ✅ **HTTP Method Coverage**: All methods (GET, POST, PUT, DELETE, PATCH)
- ✅ **Parameter Coverage**: All parameters tested (required + optional)
- ✅ **Schema Coverage**: All request/response schemas validated
- ✅ **Error Coverage**: All documented error codes tested
- ✅ **Security Coverage**: OWASP API Top 10 tested
- ✅ **Auth Coverage**: All authentication schemes tested
- ✅ **Edge Case Coverage**: Boundaries, nulls, special chars

### Quality Metrics:
- Test Generation Time: < 30 seconds for 100 endpoints
- Test Execution Time: < 5 minutes for 1000 tests (parallel)
- False Positive Rate: < 2%
- Documentation Accuracy: > 95%

---

## Next Immediate Actions

1. ✅ Review this plan
2. ⏳ Implement Phase 8.1 (Universal Parser)
3. ⏳ Implement Phase 8.2 (Semantic Analyzer)
4. ⏳ Implement Phase 8.3 (Intelligent Test Generator)
5. ⏳ Implement Phase 8.4 (Smart Data Generator)
6. ⏳ Integration testing
7. ⏳ End-to-end demo with real API docs

---

**This builds directly on our Phase 7.3 parallel execution foundation to create the world's most intelligent autonomous API testing system.**
