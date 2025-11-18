"""
Demo: State Transition Testing
Tests CREATE → READ → UPDATE → DELETE workflows and invalid transitions
"""
import asyncio
from src.workflow.dependency_graph import DependencyGraph
from src.workflow.state_transition_generator import StateTransitionGenerator

# Simple logger
class SimpleLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def warning(self, msg, **kwargs): print(f"WARN: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    def debug(self, msg, **kwargs): pass

logger = SimpleLogger()


def create_sample_endpoints():
    """Create sample API endpoints for testing"""
    return [
        # Users CRUD
        {
            "path": "/api/users",
            "method": "POST",
            "description": "Create a new user",
            "parameters": []
        },
        {
            "path": "/api/users",
            "method": "GET",
            "description": "List all users",
            "parameters": []
        },
        {
            "path": "/api/users/{id}",
            "method": "GET",
            "description": "Get a specific user",
            "parameters": [{"name": "id", "in": "path"}]
        },
        {
            "path": "/api/users/{id}",
            "method": "PUT",
            "description": "Update a user",
            "parameters": [{"name": "id", "in": "path"}]
        },
        {
            "path": "/api/users/{id}",
            "method": "DELETE",
            "description": "Delete a user",
            "parameters": [{"name": "id", "in": "path"}]
        },

        # Orders CRUD (child of users)
        {
            "path": "/api/users/{user_id}/orders",
            "method": "POST",
            "description": "Create an order for a user",
            "parameters": [{"name": "user_id", "in": "path"}]
        },
        {
            "path": "/api/users/{user_id}/orders/{id}",
            "method": "GET",
            "description": "Get a specific order",
            "parameters": [
                {"name": "user_id", "in": "path"},
                {"name": "id", "in": "path"}
            ]
        },
        {
            "path": "/api/users/{user_id}/orders/{id}",
            "method": "PUT",
            "description": "Update an order",
            "parameters": [
                {"name": "user_id", "in": "path"},
                {"name": "id", "in": "path"}
            ]
        },
        {
            "path": "/api/users/{user_id}/orders/{id}",
            "method": "DELETE",
            "description": "Delete an order",
            "parameters": [
                {"name": "user_id", "in": "path"},
                {"name": "id", "in": "path"}
            ]
        },

        # Products CRUD
        {
            "path": "/api/products",
            "method": "POST",
            "description": "Create a product",
            "parameters": []
        },
        {
            "path": "/api/products/{id}",
            "method": "GET",
            "description": "Get a product",
            "parameters": [{"name": "id", "in": "path"}]
        },
        {
            "path": "/api/products/{id}",
            "method": "PUT",
            "description": "Update a product",
            "parameters": [{"name": "id", "in": "path"}]
        },
        {
            "path": "/api/products/{id}",
            "method": "DELETE",
            "description": "Delete a product",
            "parameters": [{"name": "id", "in": "path"}]
        },

        # Incomplete CRUD (only read operations)
        {
            "path": "/api/stats",
            "method": "GET",
            "description": "Get statistics",
            "parameters": []
        },
    ]


def main():
    """Run state transition testing demo"""
    logger.info("=" * 80)
    logger.info("STATE TRANSITION TESTING DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Step 1: Create sample endpoints
    endpoints = create_sample_endpoints()
    logger.info(f"📊 Created {len(endpoints)} sample endpoints")
    logger.info("")

    # Step 2: Build dependency graph
    logger.info("🔗 Building dependency graph...")
    dep_graph = DependencyGraph()
    dep_graph.build_graph(endpoints)

    # Show graph summary
    summary = dep_graph.get_graph_summary()
    logger.info(f"   Resources found: {summary['total_resources']}")
    logger.info(f"   Dependencies detected: {summary['total_dependencies']}")
    logger.info(f"   CRUD resources: {summary['crud_resource_count']}")
    logger.info(f"   Dependency coverage: {summary['dependency_coverage']:.1f}%")
    logger.info("")

    # Show resource breakdown
    logger.info("📦 Resources:")
    for resource_name, resource in dep_graph.resources.items():
        operations = []
        if resource.create_endpoint:
            operations.append("CREATE")
        if resource.read_single_endpoint:
            operations.append("READ")
        if resource.update_endpoint:
            operations.append("UPDATE")
        if resource.delete_endpoint:
            operations.append("DELETE")

        logger.info(f"   {resource_name:15} → {', '.join(operations)}")
    logger.info("")

    # Step 3: Generate state transition sequences
    logger.info("🔄 Generating state transition sequences...")
    sequence_generator = StateTransitionGenerator(dep_graph)
    sequences = sequence_generator.generate_all_sequences()

    # Show sequence summary
    sequence_summary = sequence_generator.get_summary()
    logger.info(f"   Total sequences: {sequence_summary['total_sequences']}")
    logger.info(f"   Total transitions: {sequence_summary['total_transitions']}")
    logger.info("")

    # Show sequences by type
    logger.info("📋 Sequences by type:")
    for seq_type, count in sequence_summary['sequences_by_type'].items():
        logger.info(f"   {seq_type:30} → {count} sequences")
    logger.info("")

    # Step 4: Show detailed sequence information
    logger.info("=" * 80)
    logger.info("DETAILED SEQUENCE BREAKDOWN")
    logger.info("=" * 80)
    logger.info("")

    for i, sequence in enumerate(sequences[:10], 1):  # Show first 10
        logger.info(f"{i}. {sequence.description}")
        logger.info(f"   Resource: {sequence.resource_name}")
        logger.info(f"   Type: {sequence.sequence_type}")
        logger.info(f"   Expected outcome: {sequence.expected_outcome}")
        logger.info(f"   Transitions:")

        for j, transition in enumerate(sequence.transitions, 1):
            transition_icon = {
                'valid': '✅',
                'invalid': '❌',
                'idempotent': '🔄'
            }.get(transition.transition_type.value, '❓')

            logger.info(
                f"      {j}. {transition_icon} {transition.from_state.value:12} → "
                f"{transition.to_state.value:12} | {transition.method:6} {transition.path}"
            )
            logger.info(f"         Expected: {transition.expected_status_codes}")
            logger.info(f"         {transition.description}")

        logger.info("")

    # Step 5: Show dependency graph visualization
    logger.info("=" * 80)
    logger.info("DEPENDENCY GRAPH VISUALIZATION")
    logger.info("=" * 80)
    logger.info("")
    graph_viz = dep_graph.visualize_graph()
    logger.info(graph_viz)

    # Step 6: Test specific sequence types
    logger.info("=" * 80)
    logger.info("SEQUENCE TYPE BREAKDOWN")
    logger.info("=" * 80)
    logger.info("")

    for seq_type in sequence_summary['sequences_by_type'].keys():
        type_sequences = sequence_generator.get_sequences_by_type(seq_type)
        logger.info(f"\n{seq_type.upper()} ({len(type_sequences)} sequences):")
        for seq in type_sequences:
            logger.info(f"   - {seq.resource_name}: {seq.description}")

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("✅ Successfully generated state transition test sequences!")
    logger.info(f"📊 Total: {sequence_summary['total_sequences']} sequences covering {sequence_summary['resources_covered']} resources")
    logger.info(f"🔄 Ready to execute with StateMachineValidator")
    logger.info("")

    # Show what would happen in execution
    logger.info("💡 To execute these tests:")
    logger.info("   1. Use StateMachineValidator with real API base_url")
    logger.info("   2. Validator will execute each sequence step-by-step")
    logger.info("   3. Track state transitions and validate API behavior")
    logger.info("   4. Generate comprehensive test report")
    logger.info("")


if __name__ == "__main__":
    main()
