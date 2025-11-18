"""
Dependency Graph Builder
Analyzes API endpoints to detect dependencies and build workflow graph
Identifies: POST → GET → PUT → DELETE chains, parent-child relationships, etc.
"""
import re
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, field

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


@dataclass
class EndpointDependency:
    """Represents a dependency between two endpoints"""
    source_endpoint: str  # e.g., "POST /users"
    target_endpoint: str  # e.g., "GET /users/{id}"
    dependency_type: str  # e.g., "id_dependency", "prerequisite", "parent_child"
    shared_resource: str  # e.g., "user_id", "users"
    confidence: float  # 0.0 to 1.0
    description: str


@dataclass
class ResourceNode:
    """Represents a resource with CRUD operations"""
    resource_name: str  # e.g., "users", "orders"
    base_path: str  # e.g., "/users", "/orders"
    create_endpoint: Optional[str] = None  # POST /users
    read_list_endpoint: Optional[str] = None  # GET /users
    read_single_endpoint: Optional[str] = None  # GET /users/{id}
    update_endpoint: Optional[str] = None  # PUT /users/{id}
    delete_endpoint: Optional[str] = None  # DELETE /users/{id}
    child_resources: List[str] = field(default_factory=list)  # e.g., ["orders"]
    parent_resource: Optional[str] = None  # e.g., "users" for "/users/{id}/orders"


class DependencyGraph:
    """
    Builds and manages API endpoint dependency graph

    Detects:
    1. ID Dependencies: POST /users returns user_id → GET /users/{id} needs it
    2. CRUD Chains: POST → GET → PUT → DELETE for same resource
    3. Parent-Child: /users/{id}/orders depends on /users/{id}
    4. Prerequisites: Some endpoints must run before others
    """

    def __init__(self):
        self.dependencies: List[EndpointDependency] = []
        self.resources: Dict[str, ResourceNode] = {}
        self.endpoints: List[Dict[str, Any]] = []

    def build_graph(self, endpoints: List[Dict[str, Any]]) -> None:
        """
        Build dependency graph from list of endpoints

        Args:
            endpoints: List of endpoint definitions
        """
        self.endpoints = endpoints
        logger.info(f"🔗 Building dependency graph for {len(endpoints)} endpoints...")

        # Step 1: Extract resources and group endpoints by resource
        self._extract_resources()

        # Step 2: Detect ID dependencies (POST returns ID used by GET/PUT/DELETE)
        self._detect_id_dependencies()

        # Step 3: Detect parent-child relationships
        self._detect_parent_child_relationships()

        # Step 4: Detect CRUD chains
        self._detect_crud_chains()

        logger.info(
            f"✅ Dependency graph built: {len(self.resources)} resources, "
            f"{len(self.dependencies)} dependencies"
        )

    def _extract_resources(self) -> None:
        """
        Extract resources from endpoint paths and group CRUD operations

        Examples:
        - /users → resource: "users"
        - /users/{id} → resource: "users"
        - /users/{user_id}/orders → resource: "orders" (child of "users")
        """
        logger.debug("  Extracting resources from endpoints...")

        for endpoint in self.endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET').upper()
            endpoint_key = f"{method} {path}"

            # Extract resource name from path
            resource_name, base_path, is_child = self._parse_resource_path(path)

            if not resource_name:
                continue

            # Get or create resource node
            if resource_name not in self.resources:
                self.resources[resource_name] = ResourceNode(
                    resource_name=resource_name,
                    base_path=base_path
                )

            resource = self.resources[resource_name]

            # Classify endpoint by method and path pattern
            has_id_param = self._has_id_parameter(path)

            if method == 'POST' and not has_id_param:
                resource.create_endpoint = endpoint_key
            elif method == 'GET' and has_id_param:
                resource.read_single_endpoint = endpoint_key
            elif method == 'GET' and not has_id_param:
                resource.read_list_endpoint = endpoint_key
            elif method == 'PUT' and has_id_param:
                resource.update_endpoint = endpoint_key
            elif method == 'PATCH' and has_id_param:
                if not resource.update_endpoint:  # Prefer PUT, fallback to PATCH
                    resource.update_endpoint = endpoint_key
            elif method == 'DELETE' and has_id_param:
                resource.delete_endpoint = endpoint_key

        logger.debug(f"  Found {len(self.resources)} resources")

    def _parse_resource_path(self, path: str) -> Tuple[str, str, bool]:
        """
        Parse resource name from path

        Examples:
        - /users → ("users", "/users", False)
        - /users/{id} → ("users", "/users", False)
        - /users/{user_id}/orders → ("orders", "/users/{user_id}/orders", True)
        - /api/v1/products/{id} → ("products", "/api/v1/products", False)

        Returns:
            (resource_name, base_path, is_child)
        """
        # Remove leading/trailing slashes
        path = path.strip('/')

        # Split path into segments
        segments = path.split('/')

        # Find the last non-parameter segment (that's usually the resource)
        resource_name = None
        for i in range(len(segments) - 1, -1, -1):
            segment = segments[i]
            # Skip path parameters like {id}, {user_id}, etc.
            if not re.match(r'\{.+\}', segment):
                resource_name = segment
                break

        if not resource_name:
            return None, None, False

        # Check if this is a child resource (has ID parameter before resource)
        is_child = False
        for i, segment in enumerate(segments):
            if re.match(r'\{.+\}', segment) and i < len(segments) - 1:
                # There's an ID parameter followed by more segments
                is_child = True
                break

        # Reconstruct base path
        base_path_segments = []
        for segment in segments:
            base_path_segments.append(segment)
            # Stop at the resource name (unless it's a parameter)
            if segment == resource_name and not re.match(r'\{.+\}', segment):
                break

        base_path = '/' + '/'.join(base_path_segments)

        return resource_name, base_path, is_child

    def _has_id_parameter(self, path: str) -> bool:
        """Check if path has ID parameter like {id}, {user_id}, etc."""
        return bool(re.search(r'\{[^/]*id[^/]*\}', path, re.IGNORECASE))

    def _detect_id_dependencies(self) -> None:
        """
        Detect ID dependencies between endpoints

        Pattern: POST /users returns user_id → GET /users/{id} needs user_id

        This is the most common dependency pattern.
        """
        logger.debug("  Detecting ID dependencies...")

        for resource_name, resource in self.resources.items():
            # If resource has both CREATE and READ_SINGLE, there's an ID dependency
            if resource.create_endpoint and resource.read_single_endpoint:
                self.dependencies.append(EndpointDependency(
                    source_endpoint=resource.create_endpoint,
                    target_endpoint=resource.read_single_endpoint,
                    dependency_type='id_dependency',
                    shared_resource=f'{resource_name}_id',
                    confidence=0.95,  # Very high confidence
                    description=f'GET {resource_name} requires ID from POST {resource_name}'
                ))

            # Same for CREATE → UPDATE
            if resource.create_endpoint and resource.update_endpoint:
                self.dependencies.append(EndpointDependency(
                    source_endpoint=resource.create_endpoint,
                    target_endpoint=resource.update_endpoint,
                    dependency_type='id_dependency',
                    shared_resource=f'{resource_name}_id',
                    confidence=0.95,
                    description=f'PUT {resource_name} requires ID from POST {resource_name}'
                ))

            # Same for CREATE → DELETE
            if resource.create_endpoint and resource.delete_endpoint:
                self.dependencies.append(EndpointDependency(
                    source_endpoint=resource.create_endpoint,
                    target_endpoint=resource.delete_endpoint,
                    dependency_type='id_dependency',
                    shared_resource=f'{resource_name}_id',
                    confidence=0.95,
                    description=f'DELETE {resource_name} requires ID from POST {resource_name}'
                ))

    def _detect_parent_child_relationships(self) -> None:
        """
        Detect parent-child relationships

        Pattern: /users/{user_id}/orders depends on /users/{user_id}

        Child resources need parent resource to exist first.
        """
        logger.debug("  Detecting parent-child relationships...")

        # Group paths by pattern
        for endpoint in self.endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET').upper()
            endpoint_key = f"{method} {path}"

            # Check if path has parent-child pattern: /{parent}/{id}/{child}
            pattern = r'/([^/]+)/\{[^/]+\}/([^/{]+)'
            match = re.search(pattern, path)

            if match:
                parent_resource = match.group(1)
                child_resource = match.group(2)

                # Find parent CREATE endpoint
                if parent_resource in self.resources:
                    parent_node = self.resources[parent_resource]
                    if parent_node.create_endpoint:
                        self.dependencies.append(EndpointDependency(
                            source_endpoint=parent_node.create_endpoint,
                            target_endpoint=endpoint_key,
                            dependency_type='parent_child',
                            shared_resource=f'{parent_resource}_id',
                            confidence=0.90,
                            description=f'{child_resource} endpoint requires {parent_resource} to exist'
                        ))

                        # Update resource nodes
                        if child_resource not in parent_node.child_resources:
                            parent_node.child_resources.append(child_resource)

                        if child_resource in self.resources:
                            self.resources[child_resource].parent_resource = parent_resource

    def _detect_crud_chains(self) -> None:
        """
        Detect full CRUD chains for resources

        Pattern: POST → GET → PUT → DELETE

        This identifies complete resource lifecycle workflows.
        """
        logger.debug("  Detecting CRUD chains...")

        for resource_name, resource in self.resources.items():
            # Check if resource has complete CRUD chain
            has_create = resource.create_endpoint is not None
            has_read = resource.read_single_endpoint is not None
            has_update = resource.update_endpoint is not None
            has_delete = resource.delete_endpoint is not None

            if has_create and has_read and has_update and has_delete:
                # This is a full CRUD resource - add chain dependencies
                logger.debug(f"  Found complete CRUD chain for {resource_name}")

                # READ depends on CREATE
                # UPDATE depends on CREATE (and implicitly READ)
                # DELETE depends on CREATE (should be last)

                # These are already captured by id_dependencies, but we can add
                # additional metadata for workflow orchestration

    def get_dependencies_for_endpoint(
        self,
        endpoint_key: str
    ) -> List[EndpointDependency]:
        """
        Get all dependencies for a specific endpoint

        Args:
            endpoint_key: Endpoint key (e.g., "GET /users/{id}")

        Returns:
            List of dependencies where this endpoint is the target
        """
        return [
            dep for dep in self.dependencies
            if dep.target_endpoint == endpoint_key
        ]

    def get_execution_order(self) -> List[str]:
        """
        Get recommended execution order for endpoints based on dependencies

        Returns:
            List of endpoint keys in execution order (topological sort)
        """
        # Build adjacency list
        graph = {}
        in_degree = {}

        for endpoint in self.endpoints:
            endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"
            graph[endpoint_key] = []
            in_degree[endpoint_key] = 0

        for dep in self.dependencies:
            graph[dep.source_endpoint].append(dep.target_endpoint)
            in_degree[dep.target_endpoint] = in_degree.get(dep.target_endpoint, 0) + 1

        # Topological sort (Kahn's algorithm)
        queue = [ep for ep, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If there are cycles, append remaining endpoints
        remaining = set(in_degree.keys()) - set(result)
        result.extend(remaining)

        return result

    def get_prerequisite_endpoints(
        self,
        endpoint_key: str
    ) -> List[str]:
        """
        Get all prerequisite endpoints that must run before this one

        Args:
            endpoint_key: Endpoint key (e.g., "PUT /users/{id}")

        Returns:
            List of prerequisite endpoint keys in execution order
        """
        prerequisites = []
        visited = set()

        def dfs(ep_key):
            if ep_key in visited:
                return
            visited.add(ep_key)

            deps = self.get_dependencies_for_endpoint(ep_key)
            for dep in deps:
                dfs(dep.source_endpoint)
                if dep.source_endpoint not in prerequisites:
                    prerequisites.append(dep.source_endpoint)

        dfs(endpoint_key)
        return prerequisites

    def get_graph_summary(self) -> Dict[str, Any]:
        """
        Get summary of dependency graph

        Returns:
            Summary dict with statistics
        """
        total_endpoints = len(self.endpoints)
        total_resources = len(self.resources)
        total_dependencies = len(self.dependencies)

        # Count dependencies by type
        deps_by_type = {}
        for dep in self.dependencies:
            deps_by_type[dep.dependency_type] = deps_by_type.get(dep.dependency_type, 0) + 1

        # Count endpoints with dependencies
        endpoints_with_deps = len(set(dep.target_endpoint for dep in self.dependencies))

        # Find CRUD chains
        crud_resources = [
            name for name, res in self.resources.items()
            if res.create_endpoint and res.read_single_endpoint
            and res.update_endpoint and res.delete_endpoint
        ]

        return {
            'total_endpoints': total_endpoints,
            'total_resources': total_resources,
            'total_dependencies': total_dependencies,
            'dependencies_by_type': deps_by_type,
            'endpoints_with_dependencies': endpoints_with_deps,
            'dependency_coverage': (endpoints_with_deps / total_endpoints * 100) if total_endpoints > 0 else 0,
            'crud_resources': crud_resources,
            'crud_resource_count': len(crud_resources)
        }

    def visualize_graph(self) -> str:
        """
        Generate text visualization of dependency graph

        Returns:
            ASCII art representation of the graph
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DEPENDENCY GRAPH")
        lines.append("=" * 60)
        lines.append("")

        for resource_name, resource in self.resources.items():
            lines.append(f"📦 Resource: {resource_name}")
            lines.append(f"   Base path: {resource.base_path}")

            if resource.create_endpoint:
                lines.append(f"   ✅ CREATE: {resource.create_endpoint}")
            if resource.read_list_endpoint:
                lines.append(f"   📋 LIST:   {resource.read_list_endpoint}")
            if resource.read_single_endpoint:
                lines.append(f"   📖 READ:   {resource.read_single_endpoint}")
            if resource.update_endpoint:
                lines.append(f"   ✏️  UPDATE: {resource.update_endpoint}")
            if resource.delete_endpoint:
                lines.append(f"   🗑️  DELETE: {resource.delete_endpoint}")

            if resource.child_resources:
                lines.append(f"   👶 Children: {', '.join(resource.child_resources)}")

            lines.append("")

        lines.append("=" * 60)
        lines.append("DEPENDENCIES")
        lines.append("=" * 60)
        lines.append("")

        for dep in self.dependencies:
            lines.append(f"🔗 {dep.source_endpoint}")
            lines.append(f"   → {dep.target_endpoint}")
            lines.append(f"   Type: {dep.dependency_type}")
            lines.append(f"   Resource: {dep.shared_resource}")
            lines.append(f"   Confidence: {dep.confidence:.0%}")
            lines.append(f"   Description: {dep.description}")
            lines.append("")

        return "\n".join(lines)
