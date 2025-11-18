"""
State Transition Tester
Generates and executes workflow sequences testing state transitions
Tests: CREATE → READ → UPDATE → DELETE sequences
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

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
class StateTransition:
    """Represents a state transition in a workflow"""
    from_state: str  # e.g., "created", "read", "updated"
    to_state: str
    endpoint_key: str  # e.g., "PUT /users/{id}"
    transition_type: str  # e.g., "update", "delete", "state_change"
    description: str


@dataclass
class WorkflowSequence:
    """Represents a sequence of API calls forming a workflow"""
    resource_name: str  # e.g., "users"
    sequence_name: str  # e.g., "Full CRUD Lifecycle"
    steps: List[Dict[str, Any]]  # List of endpoint calls in order
    description: str
    expected_outcome: str


class StateTransitionTester:
    """
    Generates workflow sequences and tests state transitions

    Workflow types:
    1. CRUD Lifecycle: CREATE → READ → UPDATE → DELETE
    2. Read-Only: CREATE → READ → READ (verify idempotency)
    3. Update Cycle: CREATE → UPDATE → READ → UPDATE → READ
    4. Parent-Child: CREATE parent → CREATE child → READ child → DELETE child → DELETE parent
    """

    def __init__(self, dependency_graph):
        """
        Initialize State Transition Tester

        Args:
            dependency_graph: DependencyGraph instance
        """
        self.dependency_graph = dependency_graph
        self.workflows: List[WorkflowSequence] = []

    def generate_workflow_sequences(self) -> List[WorkflowSequence]:
        """
        Generate workflow sequences based on dependency graph

        Returns:
            List of workflow sequences to test
        """
        self.workflows = []

        logger.info("🔄 Generating workflow sequences...")

        # For each resource, generate workflow sequences
        for resource_name, resource in self.dependency_graph.resources.items():
            # 1. Full CRUD lifecycle (if all operations available)
            if self._has_full_crud(resource):
                crud_workflow = self._generate_crud_workflow(resource_name, resource)
                self.workflows.append(crud_workflow)

            # 2. Create-Read workflow (minimum viable workflow)
            if resource.create_endpoint and resource.read_single_endpoint:
                create_read_workflow = self._generate_create_read_workflow(resource_name, resource)
                self.workflows.append(create_read_workflow)

            # 3. Update cycle (create → update → verify)
            if resource.create_endpoint and resource.update_endpoint and resource.read_single_endpoint:
                update_cycle = self._generate_update_cycle_workflow(resource_name, resource)
                self.workflows.append(update_cycle)

            # 4. List before and after create
            if resource.create_endpoint and resource.read_list_endpoint:
                list_workflow = self._generate_list_workflow(resource_name, resource)
                self.workflows.append(list_workflow)

        # 5. Parent-child workflows
        parent_child_workflows = self._generate_parent_child_workflows()
        self.workflows.extend(parent_child_workflows)

        logger.info(f"✅ Generated {len(self.workflows)} workflow sequences")

        return self.workflows

    def _has_full_crud(self, resource) -> bool:
        """Check if resource has complete CRUD operations"""
        return (
            resource.create_endpoint is not None and
            resource.read_single_endpoint is not None and
            resource.update_endpoint is not None and
            resource.delete_endpoint is not None
        )

    def _generate_crud_workflow(self, resource_name: str, resource) -> WorkflowSequence:
        """
        Generate full CRUD lifecycle workflow

        Sequence: CREATE → READ → UPDATE → READ → DELETE
        """
        steps = [
            {
                'step_number': 1,
                'operation': 'CREATE',
                'endpoint_key': resource.create_endpoint,
                'description': f'Create new {resource_name}',
                'expected_status': 201,
                'extract_ids': True,  # Extract ID for subsequent steps
                'state_after': 'created'
            },
            {
                'step_number': 2,
                'operation': 'READ',
                'endpoint_key': resource.read_single_endpoint,
                'description': f'Read created {resource_name}',
                'expected_status': 200,
                'verify': 'created_data',  # Verify matches created data
                'state_after': 'verified'
            },
            {
                'step_number': 3,
                'operation': 'UPDATE',
                'endpoint_key': resource.update_endpoint,
                'description': f'Update {resource_name}',
                'expected_status': 200,
                'modify_fields': True,  # Modify some fields
                'state_after': 'updated'
            },
            {
                'step_number': 4,
                'operation': 'READ',
                'endpoint_key': resource.read_single_endpoint,
                'description': f'Verify {resource_name} was updated',
                'expected_status': 200,
                'verify': 'updated_data',  # Verify changes applied
                'state_after': 'verified_update'
            },
            {
                'step_number': 5,
                'operation': 'DELETE',
                'endpoint_key': resource.delete_endpoint,
                'description': f'Delete {resource_name}',
                'expected_status': 204,  # or 200
                'state_after': 'deleted'
            }
        ]

        return WorkflowSequence(
            resource_name=resource_name,
            sequence_name=f'Full CRUD Lifecycle - {resource_name}',
            steps=steps,
            description=f'Tests complete lifecycle: create → read → update → verify → delete',
            expected_outcome='All operations succeed, resource lifecycle completes'
        )

    def _generate_create_read_workflow(self, resource_name: str, resource) -> WorkflowSequence:
        """
        Generate simple create-read workflow

        Sequence: CREATE → READ
        """
        steps = [
            {
                'step_number': 1,
                'operation': 'CREATE',
                'endpoint_key': resource.create_endpoint,
                'description': f'Create new {resource_name}',
                'expected_status': 201,
                'extract_ids': True,
                'state_after': 'created'
            },
            {
                'step_number': 2,
                'operation': 'READ',
                'endpoint_key': resource.read_single_endpoint,
                'description': f'Read created {resource_name}',
                'expected_status': 200,
                'verify': 'created_data',
                'state_after': 'verified'
            }
        ]

        return WorkflowSequence(
            resource_name=resource_name,
            sequence_name=f'Create-Read Workflow - {resource_name}',
            steps=steps,
            description=f'Tests basic workflow: create → read and verify',
            expected_outcome='Resource created and retrieved successfully'
        )

    def _generate_update_cycle_workflow(self, resource_name: str, resource) -> WorkflowSequence:
        """
        Generate update cycle workflow

        Sequence: CREATE → UPDATE → READ → UPDATE → READ
        """
        steps = [
            {
                'step_number': 1,
                'operation': 'CREATE',
                'endpoint_key': resource.create_endpoint,
                'description': f'Create new {resource_name}',
                'expected_status': 201,
                'extract_ids': True,
                'state_after': 'created'
            },
            {
                'step_number': 2,
                'operation': 'UPDATE',
                'endpoint_key': resource.update_endpoint,
                'description': f'First update to {resource_name}',
                'expected_status': 200,
                'modify_fields': ['field_1'],
                'state_after': 'updated_once'
            },
            {
                'step_number': 3,
                'operation': 'READ',
                'endpoint_key': resource.read_single_endpoint,
                'description': f'Verify first update',
                'expected_status': 200,
                'verify': 'updated_data',
                'state_after': 'verified_update_1'
            },
            {
                'step_number': 4,
                'operation': 'UPDATE',
                'endpoint_key': resource.update_endpoint,
                'description': f'Second update to {resource_name}',
                'expected_status': 200,
                'modify_fields': ['field_2'],
                'state_after': 'updated_twice'
            },
            {
                'step_number': 5,
                'operation': 'READ',
                'endpoint_key': resource.read_single_endpoint,
                'description': f'Verify second update',
                'expected_status': 200,
                'verify': 'updated_data',
                'state_after': 'verified_update_2'
            }
        ]

        return WorkflowSequence(
            resource_name=resource_name,
            sequence_name=f'Update Cycle - {resource_name}',
            steps=steps,
            description=f'Tests multiple updates: create → update → verify → update → verify',
            expected_outcome='Multiple updates succeed and changes persist'
        )

    def _generate_list_workflow(self, resource_name: str, resource) -> WorkflowSequence:
        """
        Generate list workflow

        Sequence: LIST (count N) → CREATE → LIST (count N+1)
        """
        steps = [
            {
                'step_number': 1,
                'operation': 'LIST',
                'endpoint_key': resource.read_list_endpoint,
                'description': f'List {resource_name} before creation',
                'expected_status': 200,
                'store_count': True,  # Store initial count
                'state_after': 'counted'
            },
            {
                'step_number': 2,
                'operation': 'CREATE',
                'endpoint_key': resource.create_endpoint,
                'description': f'Create new {resource_name}',
                'expected_status': 201,
                'extract_ids': True,
                'state_after': 'created'
            },
            {
                'step_number': 3,
                'operation': 'LIST',
                'endpoint_key': resource.read_list_endpoint,
                'description': f'List {resource_name} after creation',
                'expected_status': 200,
                'verify': 'count_increased',  # Verify count increased by 1
                'state_after': 'verified_count'
            }
        ]

        return WorkflowSequence(
            resource_name=resource_name,
            sequence_name=f'List Workflow - {resource_name}',
            steps=steps,
            description=f'Tests list operations: list → create → verify count increased',
            expected_outcome='List count increases after creation'
        )

    def _generate_parent_child_workflows(self) -> List[WorkflowSequence]:
        """
        Generate parent-child workflows

        Sequence: CREATE parent → CREATE child → READ child → DELETE child → DELETE parent
        """
        workflows = []

        for resource_name, resource in self.dependency_graph.resources.items():
            if resource.child_resources:
                for child_resource_name in resource.child_resources:
                    if child_resource_name in self.dependency_graph.resources:
                        child_resource = self.dependency_graph.resources[child_resource_name]

                        # Need parent CREATE and child CREATE
                        if resource.create_endpoint and child_resource.create_endpoint:
                            workflow = self._generate_parent_child_sequence(
                                resource_name, resource, child_resource_name, child_resource
                            )
                            workflows.append(workflow)

        return workflows

    def _generate_parent_child_sequence(
        self,
        parent_name: str,
        parent_resource,
        child_name: str,
        child_resource
    ) -> WorkflowSequence:
        """Generate parent-child workflow sequence"""

        steps = [
            {
                'step_number': 1,
                'operation': 'CREATE_PARENT',
                'endpoint_key': parent_resource.create_endpoint,
                'description': f'Create parent {parent_name}',
                'expected_status': 201,
                'extract_ids': True,
                'state_after': 'parent_created'
            },
            {
                'step_number': 2,
                'operation': 'CREATE_CHILD',
                'endpoint_key': child_resource.create_endpoint,
                'description': f'Create child {child_name} under parent',
                'expected_status': 201,
                'extract_ids': True,
                'requires_parent_id': True,  # Inject parent ID
                'state_after': 'child_created'
            }
        ]

        # Add READ child if available
        if child_resource.read_single_endpoint:
            steps.append({
                'step_number': 3,
                'operation': 'READ_CHILD',
                'endpoint_key': child_resource.read_single_endpoint,
                'description': f'Read child {child_name}',
                'expected_status': 200,
                'verify': 'created_data',
                'state_after': 'child_verified'
            })

        # Add DELETE child if available
        if child_resource.delete_endpoint:
            steps.append({
                'step_number': len(steps) + 1,
                'operation': 'DELETE_CHILD',
                'endpoint_key': child_resource.delete_endpoint,
                'description': f'Delete child {child_name}',
                'expected_status': 204,
                'state_after': 'child_deleted'
            })

        # Add DELETE parent if available
        if parent_resource.delete_endpoint:
            steps.append({
                'step_number': len(steps) + 1,
                'operation': 'DELETE_PARENT',
                'endpoint_key': parent_resource.delete_endpoint,
                'description': f'Delete parent {parent_name}',
                'expected_status': 204,
                'state_after': 'parent_deleted'
            })

        return WorkflowSequence(
            resource_name=f'{parent_name}/{child_name}',
            sequence_name=f'Parent-Child Workflow - {parent_name}/{child_name}',
            steps=steps,
            description=f'Tests hierarchical workflow: create parent → create child → cleanup',
            expected_outcome='Parent and child resources created and deleted successfully'
        )

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        Get summary of generated workflows

        Returns:
            Summary dict with counts and details
        """
        workflow_types = {}
        total_steps = 0

        for workflow in self.workflows:
            workflow_type = workflow.sequence_name.split(' - ')[0]
            workflow_types[workflow_type] = workflow_types.get(workflow_type, 0) + 1
            total_steps += len(workflow.steps)

        resources_with_workflows = set(w.resource_name for w in self.workflows)

        return {
            'total_workflows': len(self.workflows),
            'total_steps': total_steps,
            'workflows_by_type': workflow_types,
            'resources_with_workflows': list(resources_with_workflows),
            'resource_count': len(resources_with_workflows)
        }

    def should_use_workflow_testing(self) -> bool:
        """
        Determine if workflow testing should be used

        Returns:
            True if at least one workflow can be generated
        """
        # Check if any resource has at least CREATE + READ
        for resource in self.dependency_graph.resources.values():
            if resource.create_endpoint and resource.read_single_endpoint:
                return True
        return False

    def visualize_workflows(self) -> str:
        """
        Generate text visualization of workflows

        Returns:
            ASCII art representation of workflows
        """
        lines = []
        lines.append("=" * 60)
        lines.append("WORKFLOW SEQUENCES")
        lines.append("=" * 60)
        lines.append("")

        for workflow in self.workflows:
            lines.append(f"🔄 {workflow.sequence_name}")
            lines.append(f"   Resource: {workflow.resource_name}")
            lines.append(f"   Description: {workflow.description}")
            lines.append(f"   Expected: {workflow.expected_outcome}")
            lines.append(f"   Steps ({len(workflow.steps)}):")

            for step in workflow.steps:
                lines.append(f"      {step['step_number']}. {step['operation']}: {step['description']}")
                lines.append(f"         Endpoint: {step['endpoint_key']}")
                lines.append(f"         Expected Status: {step['expected_status']}")
                lines.append(f"         State After: {step['state_after']}")

            lines.append("")

        return "\n".join(lines)
