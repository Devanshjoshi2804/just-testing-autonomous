"""
State Transition Generator
Generates test sequences for CRUD state transitions
Tests: CREATE → READ → UPDATE → DELETE and invalid transitions
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

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


class ResourceState(Enum):
    """Possible states for a REST resource"""
    NOT_EXISTS = "not_exists"      # Resource doesn't exist yet
    EXISTS = "exists"               # Resource exists and is active
    DELETED = "deleted"             # Resource has been deleted


class TransitionType(Enum):
    """Types of state transitions"""
    VALID = "valid"                 # Expected to succeed
    INVALID = "invalid"             # Expected to fail (testing error handling)
    IDEMPOTENT = "idempotent"      # Can repeat safely (GET, PUT)


@dataclass
class StateTransition:
    """Represents a single state transition in a test sequence"""
    from_state: ResourceState
    to_state: ResourceState
    endpoint_key: str              # e.g., "POST /users"
    method: str                    # e.g., "POST"
    path: str                      # e.g., "/users"
    transition_type: TransitionType
    expected_status_codes: List[int]  # e.g., [200, 201] for success, [404, 410] for error
    description: str
    requires_id: bool = False      # Whether this endpoint needs an ID from previous step
    payload_template: Optional[Dict[str, Any]] = None


@dataclass
class TransitionSequence:
    """A complete test sequence of state transitions"""
    resource_name: str             # e.g., "users"
    sequence_type: str             # e.g., "full_crud_lifecycle", "invalid_delete_twice"
    transitions: List[StateTransition]
    description: str
    expected_outcome: str          # "success" or "partial_failure"


class StateTransitionGenerator:
    """
    Generates state transition test sequences from dependency graph

    Generates:
    1. Valid CRUD lifecycles (CREATE → READ → UPDATE → DELETE)
    2. Invalid transitions (DELETE twice, UPDATE deleted resource)
    3. Idempotency tests (GET twice, PUT same data)
    4. State verification tests
    """

    def __init__(self, dependency_graph):
        """
        Initialize generator with dependency graph

        Args:
            dependency_graph: DependencyGraph instance with resource information
        """
        self.dependency_graph = dependency_graph
        self.sequences: List[TransitionSequence] = []

    def generate_all_sequences(self) -> List[TransitionSequence]:
        """
        Generate all state transition test sequences

        Returns:
            List of transition sequences to test
        """
        logger.info(f"🔄 Generating state transition sequences...")

        self.sequences = []

        # For each resource with CRUD operations
        for resource_name, resource in self.dependency_graph.resources.items():
            # Generate sequences for this resource
            sequences = self._generate_resource_sequences(resource_name, resource)
            self.sequences.extend(sequences)

        logger.info(
            f"✅ Generated {len(self.sequences)} state transition sequences "
            f"for {len(self.dependency_graph.resources)} resources"
        )

        return self.sequences

    def _generate_resource_sequences(
        self,
        resource_name: str,
        resource
    ) -> List[TransitionSequence]:
        """
        Generate all transition sequences for a specific resource

        Args:
            resource_name: Name of the resource (e.g., "users")
            resource: ResourceNode from dependency graph

        Returns:
            List of transition sequences
        """
        sequences = []

        # Check what CRUD operations are available
        has_create = resource.create_endpoint is not None
        has_read_single = resource.read_single_endpoint is not None
        has_update = resource.update_endpoint is not None
        has_delete = resource.delete_endpoint is not None

        # 1. Full CRUD lifecycle (if all operations available)
        if has_create and has_read_single and has_update and has_delete:
            sequences.append(self._generate_full_crud_lifecycle(resource_name, resource))

        # 2. CREATE → READ lifecycle (minimum viable)
        if has_create and has_read_single:
            sequences.append(self._generate_create_read_lifecycle(resource_name, resource))

        # 3. CREATE → UPDATE → READ lifecycle
        if has_create and has_update and has_read_single:
            sequences.append(self._generate_create_update_read_lifecycle(resource_name, resource))

        # 4. Invalid transitions (if delete available)
        if has_delete:
            # Can't delete non-existent resource
            sequences.append(self._generate_delete_nonexistent(resource_name, resource))

            # Can't delete twice
            if has_create:
                sequences.append(self._generate_delete_twice(resource_name, resource))

        # 5. Can't update non-existent resource
        if has_update:
            sequences.append(self._generate_update_nonexistent(resource_name, resource))

        # 6. Can't update deleted resource
        if has_create and has_update and has_delete:
            sequences.append(self._generate_update_after_delete(resource_name, resource))

        # 7. Idempotency tests
        if has_create and has_read_single:
            sequences.append(self._generate_read_idempotency(resource_name, resource))

        if has_create and has_update and has_read_single:
            sequences.append(self._generate_update_idempotency(resource_name, resource))

        return sequences

    def _generate_full_crud_lifecycle(self, resource_name: str, resource) -> TransitionSequence:
        """Generate complete CREATE → READ → UPDATE → READ → DELETE → READ sequence"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_read, path_read = self._parse_endpoint_key(resource.read_single_endpoint)
        method_update, path_update = self._parse_endpoint_key(resource.update_endpoint)
        method_delete, path_delete = self._parse_endpoint_key(resource.delete_endpoint)

        transitions = [
            # Step 1: CREATE resource
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create new {resource_name}",
                requires_id=False
            ),

            # Step 2: READ created resource
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200],
                description=f"Read created {resource_name}",
                requires_id=True
            ),

            # Step 3: UPDATE resource
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 204],
                description=f"Update {resource_name}",
                requires_id=True
            ),

            # Step 4: READ updated resource (verify update)
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200],
                description=f"Read updated {resource_name} (verify update)",
                requires_id=True
            ),

            # Step 5: DELETE resource
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.delete_endpoint,
                method=method_delete,
                path=path_delete,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 204],
                description=f"Delete {resource_name}",
                requires_id=True
            ),

            # Step 6: READ deleted resource (should fail)
            StateTransition(
                from_state=ResourceState.DELETED,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.INVALID,
                expected_status_codes=[404, 410],
                description=f"Read deleted {resource_name} (should fail with 404/410)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="full_crud_lifecycle",
            transitions=transitions,
            description=f"Complete CRUD lifecycle for {resource_name}: CREATE → READ → UPDATE → DELETE",
            expected_outcome="success"
        )

    def _generate_create_read_lifecycle(self, resource_name: str, resource) -> TransitionSequence:
        """Generate simple CREATE → READ sequence"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_read, path_read = self._parse_endpoint_key(resource.read_single_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create new {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200],
                description=f"Read created {resource_name}",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="create_read_lifecycle",
            transitions=transitions,
            description=f"Basic CREATE → READ lifecycle for {resource_name}",
            expected_outcome="success"
        )

    def _generate_create_update_read_lifecycle(self, resource_name: str, resource) -> TransitionSequence:
        """Generate CREATE → UPDATE → READ sequence"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_update, path_update = self._parse_endpoint_key(resource.update_endpoint)
        method_read, path_read = self._parse_endpoint_key(resource.read_single_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create new {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 204],
                description=f"Update {resource_name}",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200],
                description=f"Read updated {resource_name} (verify update)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="create_update_read_lifecycle",
            transitions=transitions,
            description=f"CREATE → UPDATE → READ lifecycle for {resource_name}",
            expected_outcome="success"
        )

    def _generate_delete_nonexistent(self, resource_name: str, resource) -> TransitionSequence:
        """Generate invalid DELETE of non-existent resource"""

        method_delete, path_delete = self._parse_endpoint_key(resource.delete_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.NOT_EXISTS,
                endpoint_key=resource.delete_endpoint,
                method=method_delete,
                path=path_delete,
                transition_type=TransitionType.INVALID,
                expected_status_codes=[404, 410],
                description=f"Try to delete non-existent {resource_name} (should fail)",
                requires_id=True  # Will use fake ID
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="delete_nonexistent",
            transitions=transitions,
            description=f"Invalid: DELETE non-existent {resource_name}",
            expected_outcome="partial_failure"
        )

    def _generate_delete_twice(self, resource_name: str, resource) -> TransitionSequence:
        """Generate invalid DELETE → DELETE sequence"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_delete, path_delete = self._parse_endpoint_key(resource.delete_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.delete_endpoint,
                method=method_delete,
                path=path_delete,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 204],
                description=f"Delete {resource_name} (first time)",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.DELETED,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.delete_endpoint,
                method=method_delete,
                path=path_delete,
                transition_type=TransitionType.INVALID,
                expected_status_codes=[404, 410],
                description=f"Try to delete {resource_name} again (should fail)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="delete_twice",
            transitions=transitions,
            description=f"Invalid: DELETE {resource_name} twice",
            expected_outcome="partial_failure"
        )

    def _generate_update_nonexistent(self, resource_name: str, resource) -> TransitionSequence:
        """Generate invalid UPDATE of non-existent resource"""

        method_update, path_update = self._parse_endpoint_key(resource.update_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.NOT_EXISTS,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.INVALID,
                expected_status_codes=[404, 410],
                description=f"Try to update non-existent {resource_name} (should fail)",
                requires_id=True  # Will use fake ID
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="update_nonexistent",
            transitions=transitions,
            description=f"Invalid: UPDATE non-existent {resource_name}",
            expected_outcome="partial_failure"
        )

    def _generate_update_after_delete(self, resource_name: str, resource) -> TransitionSequence:
        """Generate invalid CREATE → DELETE → UPDATE sequence"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_delete, path_delete = self._parse_endpoint_key(resource.delete_endpoint)
        method_update, path_update = self._parse_endpoint_key(resource.update_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.delete_endpoint,
                method=method_delete,
                path=path_delete,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 204],
                description=f"Delete {resource_name}",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.DELETED,
                to_state=ResourceState.DELETED,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.INVALID,
                expected_status_codes=[404, 410],
                description=f"Try to update deleted {resource_name} (should fail)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="update_after_delete",
            transitions=transitions,
            description=f"Invalid: UPDATE after DELETE for {resource_name}",
            expected_outcome="partial_failure"
        )

    def _generate_read_idempotency(self, resource_name: str, resource) -> TransitionSequence:
        """Generate READ → READ idempotency test"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_read, path_read = self._parse_endpoint_key(resource.read_single_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.IDEMPOTENT,
                expected_status_codes=[200],
                description=f"Read {resource_name} (first time)",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.IDEMPOTENT,
                expected_status_codes=[200],
                description=f"Read {resource_name} (second time - should return same data)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="read_idempotency",
            transitions=transitions,
            description=f"Idempotency: READ {resource_name} twice returns same data",
            expected_outcome="success"
        )

    def _generate_update_idempotency(self, resource_name: str, resource) -> TransitionSequence:
        """Generate UPDATE → UPDATE idempotency test"""

        method_create, path_create = self._parse_endpoint_key(resource.create_endpoint)
        method_update, path_update = self._parse_endpoint_key(resource.update_endpoint)
        method_read, path_read = self._parse_endpoint_key(resource.read_single_endpoint)

        transitions = [
            StateTransition(
                from_state=ResourceState.NOT_EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.create_endpoint,
                method=method_create,
                path=path_create,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200, 201],
                description=f"Create {resource_name}",
                requires_id=False
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.IDEMPOTENT,
                expected_status_codes=[200, 204],
                description=f"Update {resource_name} (first time)",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.update_endpoint,
                method=method_update,
                path=path_update,
                transition_type=TransitionType.IDEMPOTENT,
                expected_status_codes=[200, 204],
                description=f"Update {resource_name} with same data (should succeed)",
                requires_id=True
            ),
            StateTransition(
                from_state=ResourceState.EXISTS,
                to_state=ResourceState.EXISTS,
                endpoint_key=resource.read_single_endpoint,
                method=method_read,
                path=path_read,
                transition_type=TransitionType.VALID,
                expected_status_codes=[200],
                description=f"Read {resource_name} (verify final state)",
                requires_id=True
            ),
        ]

        return TransitionSequence(
            resource_name=resource_name,
            sequence_type="update_idempotency",
            transitions=transitions,
            description=f"Idempotency: UPDATE {resource_name} twice with same data",
            expected_outcome="success"
        )

    def _parse_endpoint_key(self, endpoint_key: str) -> Tuple[str, str]:
        """
        Parse endpoint key into method and path

        Args:
            endpoint_key: e.g., "POST /users"

        Returns:
            (method, path) tuple
        """
        parts = endpoint_key.split(' ', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return 'GET', endpoint_key

    def get_sequences_by_type(self, sequence_type: str) -> List[TransitionSequence]:
        """Get all sequences of a specific type"""
        return [seq for seq in self.sequences if seq.sequence_type == sequence_type]

    def get_sequences_for_resource(self, resource_name: str) -> List[TransitionSequence]:
        """Get all sequences for a specific resource"""
        return [seq for seq in self.sequences if seq.resource_name == resource_name]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of generated sequences"""
        sequences_by_type = {}
        for seq in self.sequences:
            sequences_by_type[seq.sequence_type] = sequences_by_type.get(seq.sequence_type, 0) + 1

        total_transitions = sum(len(seq.transitions) for seq in self.sequences)

        return {
            'total_sequences': len(self.sequences),
            'total_transitions': total_transitions,
            'sequences_by_type': sequences_by_type,
            'resources_covered': len(set(seq.resource_name for seq in self.sequences))
        }
