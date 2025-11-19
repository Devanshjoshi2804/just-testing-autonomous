"""
Semantic Analysis Engine
Deep understanding of API semantics, relationships, and data flows
Similar to how Claude Code understands code structure and relationships
"""
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from src.agents.base_agent import BaseAgent


class EntityType(Enum):
    """Types of entities in API"""
    USER = "user"
    RESOURCE = "resource"
    ACTION = "action"
    AUTHENTICATION = "authentication"
    PAYMENT = "payment"
    NOTIFICATION = "notification"


class RelationType(Enum):
    """Types of relationships between endpoints"""
    DEPENDS_ON = "depends_on"        # B depends on A (needs A's output)
    CREATES = "creates"               # A creates entities for B
    MODIFIES = "modifies"             # A modifies B's entities
    DELETES = "deletes"               # A deletes B's entities
    AUTHENTICATES = "authenticates"   # A provides auth for B
    VALIDATES = "validates"           # A validates before B


@dataclass
class SemanticEntity:
    """Represents a semantic entity in the API"""
    name: str
    entity_type: EntityType
    endpoints: List[str]  # Endpoints that work with this entity
    attributes: Dict[str, str]  # attribute -> type
    relationships: List[str]  # Related entities


@dataclass
class EndpointSemantics:
    """Semantic understanding of an endpoint"""
    endpoint_key: str
    intent: str  # What this endpoint does (human-readable)
    entities_used: List[str]  # Entities this endpoint works with
    data_flow_in: List[str]  # Data dependencies (from other endpoints)
    data_flow_out: List[str]  # Data this endpoint produces (for other endpoints)
    side_effects: List[str]  # Side effects (creates, modifies, deletes)
    business_value: float  # 0-1 score of business importance
    user_journey_stage: str  # Where in user journey (onboarding, core, etc)


@dataclass
class DataFlow:
    """Represents data flowing from one endpoint to another"""
    from_endpoint: str
    to_endpoint: str
    data_name: str  # e.g., "user_id", "token", "order_id"
    required: bool  # Is this data required or optional?
    transformation: Optional[str]  # How data is transformed


class SemanticAnalyzer(BaseAgent):
    """
    Analyzes APIs to understand their semantic structure

    Similar to how Claude Code understands code:
    - Identifies entities and their relationships
    - Understands data flows between endpoints
    - Recognizes patterns (CRUD, auth flows, etc)
    - Infers business logic and constraints
    - Maps user journeys through API
    """

    def __init__(self):
        super().__init__(agent_name="SemanticAnalyzer", use_fast_llm=False)
        self.entities: Dict[str, SemanticEntity] = {}
        self.endpoint_semantics: Dict[str, EndpointSemantics] = {}
        self.data_flows: List[DataFlow] = []

    async def analyze_api_structure(
        self,
        endpoints: List[Dict[str, Any]],
        documentation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deeply analyze API structure to understand semantics

        Args:
            endpoints: List of endpoints from OpenAPI spec
            documentation: Optional additional documentation

        Returns:
            Semantic analysis results
        """
        logger.info(f"🔍 Analyzing semantic structure of {len(endpoints)} endpoints...")

        # Extract entities from API
        await self._extract_entities(endpoints)

        # Analyze each endpoint's semantics
        for endpoint in endpoints:
            semantics = await self._analyze_endpoint_semantics(endpoint)
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
            self.endpoint_semantics[endpoint_key] = semantics

        # Infer data flows between endpoints
        self._infer_data_flows()

        # Identify critical paths
        critical_paths = self._identify_critical_paths()

        # Build knowledge graph
        knowledge_graph = self._build_knowledge_graph()

        logger.info(f"✅ Semantic analysis complete: {len(self.entities)} entities, "
                   f"{len(self.data_flows)} data flows, {len(critical_paths)} critical paths")

        return {
            "entities": {name: self._entity_to_dict(e) for name, e in self.entities.items()},
            "endpoint_semantics": {k: self._semantics_to_dict(s) for k, s in self.endpoint_semantics.items()},
            "data_flows": [self._flow_to_dict(f) for f in self.data_flows],
            "critical_paths": critical_paths,
            "knowledge_graph": knowledge_graph
        }

    async def _extract_entities(self, endpoints: List[Dict[str, Any]]):
        """Extract semantic entities from API endpoints"""

        # Build prompt with all endpoints
        endpoints_summary = "\n".join([
            f"- {ep.get('method')} {ep.get('path')}: {ep.get('summary', 'N/A')}"
            for ep in endpoints[:20]  # Limit to first 20 for context
        ])

        prompt = f"""Analyze these API endpoints and identify the main entities (resources/objects) in the system.

ENDPOINTS:
{endpoints_summary}

For each entity, provide:
1. Entity name (e.g., "user", "product", "order")
2. Entity type (user/resource/action/authentication/payment/notification)
3. Which endpoints work with this entity

Respond with JSON array:
[
  {{"name": "user", "type": "user", "endpoints": ["POST /users", "GET /users/{{id}}"]}},
  {{"name": "order", "type": "resource", "endpoints": ["POST /orders", "GET /orders/{{id}}"]}},
  ...
]"""

        try:
            response = self.invoke(prompt)
            entities_data = self.parse_json_response(response)

            if isinstance(entities_data, list):
                for ent_data in entities_data:
                    entity = SemanticEntity(
                        name=ent_data.get('name', ''),
                        entity_type=EntityType(ent_data.get('type', 'resource')),
                        endpoints=ent_data.get('endpoints', []),
                        attributes={},
                        relationships=[]
                    )
                    self.entities[entity.name] = entity

            logger.info(f"📦 Extracted {len(self.entities)} entities")

        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            # Fallback: extract from paths
            self._extract_entities_from_paths(endpoints)

    def _extract_entities_from_paths(self, endpoints: List[Dict[str, Any]]):
        """Fallback: extract entities from URL paths"""
        entity_names = set()

        for endpoint in endpoints:
            path = endpoint.get('path', '')
            parts = path.strip('/').split('/')

            # First path segment is usually the entity
            if parts and parts[0] and not parts[0].startswith('{'):
                entity_names.add(parts[0].lower().rstrip('s'))  # Remove plural 's'

        for name in entity_names:
            self.entities[name] = SemanticEntity(
                name=name,
                entity_type=EntityType.RESOURCE,
                endpoints=[],
                attributes={},
                relationships=[]
            )

        logger.info(f"📦 Extracted {len(entity_names)} entities (fallback method)")

    async def _analyze_endpoint_semantics(
        self,
        endpoint: Dict[str, Any]
    ) -> EndpointSemantics:
        """Analyze the semantic meaning of a single endpoint"""

        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '')
        summary = endpoint.get('summary', '')

        prompt = f"""Analyze this API endpoint and describe its semantic meaning.

ENDPOINT: {endpoint_key}
Method: {method}
Summary: {summary}
Parameters: {endpoint.get('parameters', [])}

Provide:
1. INTENT: What does this endpoint do? (1 sentence)
2. ENTITIES: What entities (resources) does it work with?
3. SIDE_EFFECTS: What does it create/modify/delete?
4. BUSINESS_VALUE: Rate business importance (0-1)
5. USER_JOURNEY_STAGE: onboarding/authentication/core_functionality/payment/completion

Respond with JSON:
{{
  "intent": "Creates a new user account",
  "entities": ["user"],
  "side_effects": ["creates user"],
  "business_value": 0.9,
  "user_journey_stage": "onboarding"
}}"""

        try:
            response = self.invoke(prompt)
            data = self.parse_json_response(response)

            return EndpointSemantics(
                endpoint_key=endpoint_key,
                intent=data.get('intent', f'{method} {path}'),
                entities_used=data.get('entities', []),
                data_flow_in=[],  # Will be filled by _infer_data_flows
                data_flow_out=[],
                side_effects=data.get('side_effects', []),
                business_value=float(data.get('business_value', 0.5)),
                user_journey_stage=data.get('user_journey_stage', 'core_functionality')
            )

        except Exception as e:
            logger.debug(f"Semantic analysis failed for {endpoint_key}: {e}")
            return self._fallback_semantics(endpoint)

    def _fallback_semantics(self, endpoint: Dict[str, Any]) -> EndpointSemantics:
        """Fallback semantic analysis based on heuristics"""
        endpoint_key = f"{endpoint.get('method')} {endpoint.get('path')}"
        method = endpoint.get('method', 'GET')
        path = endpoint.get('path', '')

        # Infer intent from method and path
        if method == 'POST':
            intent = f"Create {path.split('/')[-1]}"
        elif method == 'GET':
            intent = f"Retrieve {path.split('/')[-1]}"
        elif method == 'PUT':
            intent = f"Update {path.split('/')[-1]}"
        elif method == 'DELETE':
            intent = f"Delete {path.split('/')[-1]}"
        else:
            intent = f"{method} {path}"

        # Extract entity from path
        path_parts = path.strip('/').split('/')
        entity = path_parts[0].lower().rstrip('s') if path_parts else 'resource'

        # Determine side effects
        side_effects = []
        if method == 'POST':
            side_effects.append(f'creates {entity}')
        elif method in ['PUT', 'PATCH']:
            side_effects.append(f'modifies {entity}')
        elif method == 'DELETE':
            side_effects.append(f'deletes {entity}')

        # Business value heuristics
        business_value = 0.5
        if 'payment' in path.lower() or 'order' in path.lower():
            business_value = 0.9
        elif 'auth' in path.lower() or 'login' in path.lower():
            business_value = 0.8

        return EndpointSemantics(
            endpoint_key=endpoint_key,
            intent=intent,
            entities_used=[entity],
            data_flow_in=[],
            data_flow_out=[],
            side_effects=side_effects,
            business_value=business_value,
            user_journey_stage='core_functionality'
        )

    def _infer_data_flows(self):
        """Infer data flow relationships between endpoints"""

        # Common patterns
        # 1. POST /users -> creates user_id -> used by other endpoints
        # 2. POST /auth/login -> creates token -> used by authenticated endpoints
        # 3. POST /orders -> creates order_id -> used by GET /orders/{id}

        for from_key, from_sem in self.endpoint_semantics.items():
            from_method = from_key.split()[0]
            from_path = from_key.split(maxsplit=1)[1] if ' ' in from_key else ''

            # If POST/PUT, likely creates data
            if from_method in ['POST', 'PUT']:
                # Extract what it creates
                for side_effect in from_sem.side_effects:
                    if 'creates' in side_effect:
                        # This creates some data
                        created_entity = side_effect.split('creates')[-1].strip()
                        created_id = f"{created_entity}_id"

                        # Find endpoints that might use this data
                        for to_key, to_sem in self.endpoint_semantics.items():
                            to_path = to_key.split(maxsplit=1)[1] if ' ' in to_key else ''

                            # If path has {id} parameter and related entity
                            if '{' in to_path and created_entity in to_path:
                                flow = DataFlow(
                                    from_endpoint=from_key,
                                    to_endpoint=to_key,
                                    data_name=created_id,
                                    required=True,
                                    transformation=None
                                )
                                self.data_flows.append(flow)

                                # Update semantics
                                from_sem.data_flow_out.append(created_id)
                                to_sem.data_flow_in.append(created_id)

        logger.info(f"🔄 Inferred {len(self.data_flows)} data flows")

    def _identify_critical_paths(self) -> List[Dict[str, Any]]:
        """Identify critical user journeys through the API"""

        critical_paths = []

        # Group endpoints by journey stage
        stages = {}
        for key, sem in self.endpoint_semantics.items():
            stage = sem.user_journey_stage
            if stage not in stages:
                stages[stage] = []
            stages[stage].append((key, sem))

        # Define typical journey order
        journey_order = ['onboarding', 'authentication', 'core_functionality', 'payment', 'completion']

        # Build critical paths
        for i, stage in enumerate(journey_order):
            if stage in stages:
                # Get highest business value endpoint in this stage
                best = max(stages[stage], key=lambda x: x[1].business_value)
                critical_paths.append({
                    'stage': stage,
                    'endpoint': best[0],
                    'intent': best[1].intent,
                    'business_value': best[1].business_value,
                    'order': i
                })

        return critical_paths

    def _build_knowledge_graph(self) -> Dict[str, Any]:
        """Build knowledge graph of API structure"""

        graph = {
            'nodes': [],
            'edges': []
        }

        # Add entity nodes
        for name, entity in self.entities.items():
            graph['nodes'].append({
                'id': name,
                'type': 'entity',
                'entity_type': entity.entity_type.value
            })

        # Add endpoint nodes
        for key, sem in self.endpoint_semantics.items():
            graph['nodes'].append({
                'id': key,
                'type': 'endpoint',
                'business_value': sem.business_value,
                'journey_stage': sem.user_journey_stage
            })

        # Add edges (data flows)
        for flow in self.data_flows:
            graph['edges'].append({
                'from': flow.from_endpoint,
                'to': flow.to_endpoint,
                'label': flow.data_name,
                'required': flow.required
            })

        return graph

    def get_endpoint_dependencies(self, endpoint_key: str) -> List[str]:
        """Get list of endpoints that this endpoint depends on"""
        dependencies = []

        if endpoint_key in self.endpoint_semantics:
            sem = self.endpoint_semantics[endpoint_key]
            for data in sem.data_flow_in:
                # Find which endpoint provides this data
                for flow in self.data_flows:
                    if flow.to_endpoint == endpoint_key and flow.data_name == data:
                        dependencies.append(flow.from_endpoint)

        return dependencies

    def get_optimal_test_order(self, endpoints: List[str]) -> List[str]:
        """Get optimal order to test endpoints based on dependencies"""

        # Topological sort based on dependencies
        in_degree = {ep: 0 for ep in endpoints}
        graph = {ep: [] for ep in endpoints}

        # Build dependency graph
        for ep in endpoints:
            deps = self.get_endpoint_dependencies(ep)
            for dep in deps:
                if dep in graph:
                    graph[dep].append(ep)
                    in_degree[ep] += 1

        # Topological sort
        queue = [ep for ep in endpoints if in_degree[ep] == 0]
        result = []

        while queue:
            # Sort by business value to prioritize important endpoints
            queue.sort(key=lambda ep: self.endpoint_semantics.get(ep, self._fallback_semantics({})).business_value, reverse=True)
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add any remaining endpoints (circular dependencies)
        for ep in endpoints:
            if ep not in result:
                result.append(ep)

        return result

    def _entity_to_dict(self, entity: SemanticEntity) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        return {
            'name': entity.name,
            'type': entity.entity_type.value,
            'endpoints': entity.endpoints,
            'attributes': entity.attributes
        }

    def _semantics_to_dict(self, sem: EndpointSemantics) -> Dict[str, Any]:
        """Convert semantics to dictionary"""
        return {
            'intent': sem.intent,
            'entities_used': sem.entities_used,
            'data_flow_in': sem.data_flow_in,
            'data_flow_out': sem.data_flow_out,
            'side_effects': sem.side_effects,
            'business_value': sem.business_value,
            'user_journey_stage': sem.user_journey_stage
        }

    def _flow_to_dict(self, flow: DataFlow) -> Dict[str, Any]:
        """Convert data flow to dictionary"""
        return {
            'from': flow.from_endpoint,
            'to': flow.to_endpoint,
            'data': flow.data_name,
            'required': flow.required
        }


# Global analyzer instance
_analyzer: Optional[SemanticAnalyzer] = None


def get_semantic_analyzer() -> SemanticAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SemanticAnalyzer()
    return _analyzer
