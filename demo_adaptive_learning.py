"""
Demo: Adaptive Constraint Learning
Demonstrates learning constraints from API error responses
"""
from src.learning.error_message_parser import ErrorMessageParser, ConstraintType
from src.learning.constraint_learner import ConstraintLearner
from src.learning.constraint_updater import ConstraintUpdater

# Simple logger
class SimpleLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def warning(self, msg, **kwargs): print(f"WARN: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    def debug(self, msg, **kwargs): pass

logger = SimpleLogger()


def demo_parse_error_messages():
    """Demo: Parse error messages and extract constraints"""
    logger.info("=" * 80)
    logger.info("DEMO 1: Error Message Parsing")
    logger.info("=" * 80)
    logger.info("")

    parser = ErrorMessageParser()

    # Sample error messages
    error_messages = [
        ("age must be >= 18", "age"),
        ("name must be at least 3 characters", "name"),
        ("email must be a valid email", "email"),
        ("status must be one of: active, inactive, pending", "status"),
        ("field 'username' is required", None),
        ("price cannot exceed 999.99", "price"),
        ("description must be at most 500 characters", "description"),
        ("id already exists", "id"),
    ]

    logger.info("Parsing error messages:")
    logger.info("")

    for error_msg, field_name in error_messages:
        logger.info(f"Error: \"{error_msg}\"")

        constraints = parser.parse_error_message(error_msg, field_name)

        if constraints:
            for constraint in constraints:
                logger.info(f"   ✅ Parsed: {constraint.constraint_type.value}")
                logger.info(f"      Field: {constraint.field_name}")
                logger.info(f"      Value: {constraint.value}")
                logger.info(f"      Confidence: {constraint.confidence:.0%}")
        else:
            logger.warning("   ⚠️  No constraints parsed")

        logger.info("")


def demo_parse_error_response():
    """Demo: Parse structured error responses"""
    logger.info("=" * 80)
    logger.info("DEMO 2: Parse Structured Error Response")
    logger.info("=" * 80)
    logger.info("")

    parser = ErrorMessageParser()

    # Sample error response from API
    error_response = {
        "error": "validation_error",
        "message": "Request validation failed",
        "details": {
            "age": "age must be >= 18",
            "email": "invalid email format",
            "username": "username must be at least 3 characters"
        }
    }

    logger.info("Error response:")
    logger.info(f"   {error_response}")
    logger.info("")

    constraints = parser.parse_error_response(
        error_response,
        status_code=422,
        endpoint="POST /users"
    )

    logger.info(f"Parsed {len(constraints)} constraints:")
    logger.info("")

    for constraint in constraints:
        logger.info(f"• {constraint.field_name}.{constraint.constraint_type.value} = {constraint.value}")
        logger.info(f"  Confidence: {constraint.confidence:.0%}")
        logger.info("")


def demo_constraint_learning():
    """Demo: Learn constraints from multiple error responses"""
    logger.info("=" * 80)
    logger.info("DEMO 3: Constraint Learning")
    logger.info("=" * 80)
    logger.info("")

    learner = ConstraintLearner(min_confidence=0.7)

    # Simulate multiple error responses
    error_responses = [
        {
            "endpoint": "POST /users",
            "status": 422,
            "body": {
                "error": "validation_error",
                "details": {
                    "age": "age must be >= 18",
                    "name": "name must be at least 3 characters"
                }
            }
        },
        {
            "endpoint": "POST /users",
            "status": 422,
            "body": {
                "error": "validation_error",
                "details": {
                    "email": "invalid email format",
                    "age": "age must be >= 18"  # Same constraint again!
                }
            }
        },
        {
            "endpoint": "POST /products",
            "status": 422,
            "body": {
                "error": "validation_error",
                "details": {
                    "price": "price cannot exceed 9999.99",
                    "name": "name is required"
                }
            }
        }
    ]

    logger.info("Processing error responses...")
    logger.info("")

    for i, error in enumerate(error_responses, 1):
        logger.info(f"Error Response {i}: {error['endpoint']} ({error['status']})")

        learner.learn_from_error_response(
            response_body=error['body'],
            status_code=error['status'],
            endpoint=error['endpoint']
        )

        logger.info("")

    # Get learning statistics
    stats = learner.get_statistics()

    logger.info("=" * 80)
    logger.info("Learning Statistics:")
    logger.info(f"   Total errors processed: {stats['total_errors_processed']}")
    logger.info(f"   Total constraints learned: {stats['total_constraints_learned']}")
    logger.info(f"   High confidence: {stats['high_confidence_count']}")
    logger.info("")

    logger.info("Constraints by type:")
    for constraint_type, count in stats['constraints_by_type'].items():
        logger.info(f"   {constraint_type}: {count}")
    logger.info("")

    # Get constraints for specific endpoint
    logger.info("Learned constraints for POST /users:")
    user_constraints = learner.get_constraints_for_endpoint("POST /users")

    for field_name, constraints in user_constraints.items():
        logger.info(f"   {field_name}:")
        for key, value in constraints.items():
            logger.info(f"      {key}: {value}")
    logger.info("")

    logger.info("Learned constraints for POST /products:")
    product_constraints = learner.get_constraints_for_endpoint("POST /products")

    for field_name, constraints in product_constraints.items():
        logger.info(f"   {field_name}:")
        for key, value in constraints.items():
            logger.info(f"      {key}: {value}")
    logger.info("")

    return learner


def demo_constraint_updating():
    """Demo: Update existing constraints with learned information"""
    logger.info("=" * 80)
    logger.info("DEMO 4: Constraint Updating")
    logger.info("=" * 80)
    logger.info("")

    # Existing constraints (from documentation)
    existing_constraints = {
        "age": {
            "type": "integer",
            "min": 0,
            "max": 200
        },
        "name": {
            "type": "string",
            "max_length": 100
        }
    }

    # Learned constraints (from error responses)
    learned_constraints = {
        "age": {
            "min": 18  # More restrictive minimum!
        },
        "name": {
            "min_length": 3,  # New constraint!
            "required": True  # New constraint!
        },
        "email": {  # Completely new field!
            "type": "string",
            "format": "email",
            "required": True
        }
    }

    logger.info("Existing constraints (from docs):")
    for field, constraints in existing_constraints.items():
        logger.info(f"   {field}: {constraints}")
    logger.info("")

    logger.info("Learned constraints (from errors):")
    for field, constraints in learned_constraints.items():
        logger.info(f"   {field}: {constraints}")
    logger.info("")

    # Test different merge strategies
    updater = ConstraintUpdater()

    # Strategy 1: Conservative (only add new)
    logger.info("=" * 40)
    logger.info("Merge Strategy: CONSERVATIVE")
    logger.info("=" * 40)
    logger.info("")

    conservative_result = updater.update_constraints(
        existing_constraints,
        learned_constraints,
        merge_strategy='conservative'
    )

    logger.info("Result:")
    for field, constraints in conservative_result.items():
        logger.info(f"   {field}: {constraints}")
    logger.info("")

    updater.clear_history()

    # Strategy 2: Aggressive (update with more restrictive)
    logger.info("=" * 40)
    logger.info("Merge Strategy: AGGRESSIVE")
    logger.info("=" * 40)
    logger.info("")

    aggressive_result = updater.update_constraints(
        existing_constraints,
        learned_constraints,
        merge_strategy='aggressive'
    )

    logger.info("Result:")
    for field, constraints in aggressive_result.items():
        logger.info(f"   {field}: {constraints}")
    logger.info("")

    logger.info("Key changes:")
    logger.info("   • age.min: 0 → 18 (more restrictive, updated)")
    logger.info("   • age.max: 200 (kept existing, less restrictive)")
    logger.info("   • name.min_length: 3 (new constraint, added)")
    logger.info("   • email: {...} (new field, added)")
    logger.info("")


def demo_adaptive_feedback_loop():
    """Demo: Complete adaptive learning feedback loop"""
    logger.info("=" * 80)
    logger.info("DEMO 5: Adaptive Feedback Loop")
    logger.info("=" * 80)
    logger.info("")

    logger.info("Simulating 3 iterations of adaptive learning:")
    logger.info("")

    # Initial constraints (empty)
    constraints = {}
    learner = ConstraintLearner()
    updater = ConstraintUpdater()

    # Iteration 1: First errors
    logger.info("--- ITERATION 1 ---")
    logger.info("Current constraints: (empty)")
    logger.info("")

    error1 = {
        "error": "validation_error",
        "details": {
            "age": "age must be >= 18",
            "email": "invalid email format"
        }
    }

    learner.learn_from_error_response(error1, 422, "POST /users")
    learned1 = learner.get_constraints_for_endpoint("POST /users")

    constraints = updater.update_constraints(constraints, learned1, 'aggressive')

    logger.info(f"After iteration 1: {len(constraints)} fields")
    for field, c in constraints.items():
        logger.info(f"   {field}: {c}")
    logger.info("")

    # Iteration 2: More specific errors
    logger.info("--- ITERATION 2 ---")
    logger.info(f"Current constraints: {len(constraints)} fields")
    logger.info("")

    error2 = {
        "error": "validation_error",
        "details": {
            "age": "age cannot exceed 150",  # New upper bound!
            "name": "name must be at least 3 characters"
        }
    }

    learner.learn_from_error_response(error2, 422, "POST /users")
    learned2 = learner.get_constraints_for_endpoint("POST /users")

    constraints = updater.update_constraints(constraints, learned2, 'aggressive')

    logger.info(f"After iteration 2: {len(constraints)} fields")
    for field, c in constraints.items():
        logger.info(f"   {field}: {c}")
    logger.info("")

    # Iteration 3: Required field errors
    logger.info("--- ITERATION 3 ---")
    logger.info(f"Current constraints: {len(constraints)} fields")
    logger.info("")

    error3 = {
        "error": "missing_required_fields",
        "details": {
            "email": "field 'email' is required",
            "username": "field 'username' is required"
        }
    }

    learner.learn_from_error_response(error3, 422, "POST /users")
    learned3 = learner.get_constraints_for_endpoint("POST /users")

    constraints = updater.update_constraints(constraints, learned3, 'aggressive')

    logger.info(f"After iteration 3: {len(constraints)} fields")
    for field, c in constraints.items():
        logger.info(f"   {field}: {c}")
    logger.info("")

    # Show final statistics
    logger.info("=" * 80)
    logger.info("FINAL STATISTICS")
    logger.info("=" * 80)
    logger.info("")

    stats = learner.get_statistics()
    logger.info(f"Total errors processed: {stats['total_errors_processed']}")
    logger.info(f"Total constraints learned: {stats['total_constraints_learned']}")
    logger.info(f"Final constraint count: {len(constraints)} fields")
    logger.info("")

    logger.info("✅ Feedback loop complete!")
    logger.info("   The system learned constraints from errors and improved over time")
    logger.info("")


def main():
    """Run all adaptive learning demos"""
    logger.info("=" * 80)
    logger.info("ADAPTIVE CONSTRAINT LEARNING DEMO")
    logger.info("=" * 80)
    logger.info("")

    # Demo 1: Parse error messages
    demo_parse_error_messages()

    # Demo 2: Parse structured error responses
    demo_parse_error_response()

    # Demo 3: Learn constraints from multiple errors
    demo_constraint_learning()

    # Demo 4: Update existing constraints
    demo_constraint_updating()

    # Demo 5: Complete feedback loop
    demo_adaptive_feedback_loop()

    # Summary
    logger.info("=" * 80)
    logger.info("DEMO COMPLETE")
    logger.info("=" * 80)
    logger.info("")

    logger.info("✅ Adaptive learning features demonstrated:")
    logger.info("   1. Error message parsing (20+ patterns)")
    logger.info("   2. Constraint extraction (9 types)")
    logger.info("   3. Confidence-based learning")
    logger.info("   4. Constraint merging strategies")
    logger.info("   5. Complete feedback loop")
    logger.info("")

    logger.info("🎯 Integration with TestRunner:")
    logger.info("   runner = TestRunner(...)")
    logger.info("   results = await runner.test_with_adaptive_learning(")
    logger.info("       endpoints=endpoints,")
    logger.info("       iterations=3,")
    logger.info("       merge_strategy='aggressive'")
    logger.info("   )")
    logger.info("")

    logger.info("📊 Benefits:")
    logger.info("   ✓ Learn from API errors automatically")
    logger.info("   ✓ Improve test data generation over time")
    logger.info("   ✓ Discover undocumented constraints")
    logger.info("   ✓ Reduce false positives")
    logger.info("   ✓ Create self-improving test system")
    logger.info("")

    logger.info("🔄 Supported constraint types:")
    logger.info("   • Minimum/maximum values")
    logger.info("   • String length constraints")
    logger.info("   • Format requirements (email, URL, UUID, etc.)")
    logger.info("   • Enum values")
    logger.info("   • Required fields")
    logger.info("   • Type constraints")
    logger.info("   • Unique constraints")
    logger.info("")


if __name__ == "__main__":
    main()
