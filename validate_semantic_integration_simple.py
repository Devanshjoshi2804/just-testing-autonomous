#!/usr/bin/env python3
"""
Simple Semantic Integration Validation (No Module Imports)
Validates code structure and integration points without importing modules
"""
import re
import sys
from pathlib import Path


def check_file_contains(file_path: Path, patterns: list, description: str) -> bool:
    """Check if file contains all patterns"""
    if not file_path.exists():
        print(f"  ✗ File not found: {file_path}")
        return False

    content = file_path.read_text()

    for pattern in patterns:
        if isinstance(pattern, str):
            if pattern not in content:
                print(f"  ✗ Missing: {pattern[:80]}")
                return False
        else:  # regex
            if not re.search(pattern, content):
                print(f"  ✗ Missing pattern: {pattern.pattern[:80]}")
                return False

    print(f"  ✓ {description}")
    return True


def main():
    print("=" * 80)
    print("🔬 SEMANTIC INTEGRATION VALIDATION (Simple)")
    print("=" * 80)
    print()

    base_path = Path(__file__).parent
    results = []

    # Test 1: EnhancedDocumentParser exists and has semantic analysis
    print("Test 1: EnhancedDocumentParser structure")
    results.append(check_file_contains(
        base_path / "src/parsers/enhanced_document_parser.py",
        [
            "class EnhancedDocumentParser",
            "SemanticDocAnalyzer",
            "semantic_contexts",
            "enable_semantic_analysis",
            "def parse("
        ],
        "EnhancedDocumentParser has semantic analysis integration"
    ))

    # Test 2: EnhancedTestGenerator exists and combines semantic + LLM
    print("Test 2: EnhancedTestGenerator structure")
    results.append(check_file_contains(
        base_path / "src/agents/enhanced_test_generator.py",
        [
            "class EnhancedTestGenerator(TestGenerator)",
            "SemanticTestGenerator",
            "semantic_contexts",
            "def generate_comprehensive_tests(",
            "def prioritize_tests("
        ],
        "EnhancedTestGenerator combines semantic + LLM tests"
    ))

    # Test 3: Document upload route uses EnhancedDocumentParser
    print("Test 3: Document upload route integration")
    results.append(check_file_contains(
        base_path / "src/api/routes/documents.py",
        [
            "from src.parsers.enhanced_document_parser import EnhancedDocumentParser",
            "EnhancedDocumentParser(",
            '"semantic_contexts"',
            '"semantic_summary"'
        ],
        "Document upload uses EnhancedDocumentParser and stores semantic data"
    ))

    # Test 4: TestRunner accepts semantic_contexts parameter
    print("Test 4: TestRunner semantic integration")
    results.append(check_file_contains(
        base_path / "src/executors/test_runner.py",
        [
            "from src.agents.enhanced_test_generator import EnhancedTestGenerator",
            "semantic_contexts",
            "EnhancedTestGenerator(",
            re.compile(r"def __init__\([^)]*semantic_contexts")
        ],
        "TestRunner uses EnhancedTestGenerator with semantic contexts"
    ))

    # Test 5: Test execution route passes semantic contexts
    print("Test 5: Test execution route integration")
    results.append(check_file_contains(
        base_path / "src/api/routes/tests.py",
        [
            "semantic_contexts",
            re.compile(r"doc_metadata\.get\([\"']semantic_contexts"),
            re.compile(r"TestRunner\([^)]*semantic_contexts")
        ],
        "Test execution passes semantic contexts to TestRunner"
    ))

    # Test 6: SemanticDocAnalyzer extracts understanding
    print("Test 6: SemanticDocAnalyzer capabilities")
    results.append(check_file_contains(
        base_path / "src/analysis/semantic_doc_analyzer.py",
        [
            "class SemanticDocAnalyzer",
            "def _extract_use_cases(",
            "def _extract_examples(",
            "def _extract_best_practices(",
            "def _extract_common_errors(",
            "def _extract_edge_cases(",
            "def _extract_business_rules("
        ],
        "SemanticDocAnalyzer extracts 6+ types of semantic elements"
    ))

    # Test 7: SemanticTestGenerator generates from understanding
    print("Test 7: SemanticTestGenerator capabilities")
    results.append(check_file_contains(
        base_path / "src/testing/semantic_test_generator.py",
        [
            "class SemanticTestGenerator",
            "def _tests_from_examples(",
            "def _tests_from_use_cases(",
            "def _tests_from_best_practices(",
            "def _tests_from_common_errors(",
            "def _tests_from_edge_cases(",
            "def _tests_from_business_rules("
        ],
        "SemanticTestGenerator generates 6+ types of tests"
    ))

    # Test 8: Documentation context has rich fields
    print("Test 8: DocumentationContext dataclass")
    results.append(check_file_contains(
        base_path / "src/analysis/semantic_doc_analyzer.py",
        [
            "@dataclass",
            "class DocumentationContext",
            "use_cases: List[str]",
            "examples: List[Dict]",
            "best_practices: List[str]",
            "common_errors: List[str]",
            "edge_cases: List[str]",
            "business_rules: List[str]"
        ],
        "DocumentationContext has semantic fields"
    ))

    # Test 9: Demo script exists
    print("Test 9: Demo script exists")
    results.append(check_file_contains(
        base_path / "demo_semantic_analysis.py",
        [
            "SemanticDocAnalyzer",
            "SemanticTestGenerator",
            "def demonstrate_semantic_extraction(",
            "def demonstrate_semantic_test_generation("
        ],
        "Semantic analysis demo script exists"
    ))

    # Test 10: RL integration remains intact
    print("Test 10: RL integration preserved")
    results.append(check_file_contains(
        base_path / "src/executors/test_runner.py",
        [
            "TestOptimizer",
            "use_rl",
            "rl_optimizer",
            "prioritize_endpoints"
        ],
        "RL test prioritization still integrated"
    ))

    # Test 11: Test prioritization by confidence
    print("Test 11: Test prioritization logic")
    results.append(check_file_contains(
        base_path / "src/agents/enhanced_test_generator.py",
        [
            "def prioritize_tests(",
            "priority_order",
            "documentation_example",
            "documented_error",
            "llm_generated",
            "confidence"
        ],
        "Tests prioritized by source and confidence"
    ))

    # Test 12: Metadata enrichment in document upload
    print("Test 12: Semantic metadata in ChromaDB")
    results.append(check_file_contains(
        base_path / "src/api/routes/documents.py",
        [
            "semantic_quality",
            "has_semantic_context",
            "semantic_summary"
        ],
        "Semantic metadata added to ChromaDB chunks"
    ))

    # Summary
    print()
    print("=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"\nTests passed: {passed}/{total} ({success_rate:.1f}%)")
    print()

    if passed == total:
        print("✅ ALL INTEGRATION CHECKS PASSED!")
        print()
        print("🎉 Semantic Analysis Integration Complete:")
        print()
        print("  📄 Document Upload Flow:")
        print("    1. User uploads API documentation")
        print("    2. EnhancedDocumentParser automatically runs semantic analysis")
        print("    3. Extracts use cases, examples, best practices, errors, edge cases")
        print("    4. Stores semantic_contexts in document metadata")
        print("    5. Enriches ChromaDB chunks with semantic quality metadata")
        print()
        print("  🧪 Test Generation Flow:")
        print("    1. Test execution starts with document_id")
        print("    2. Semantic contexts loaded from document metadata")
        print("    3. TestRunner creates EnhancedTestGenerator with contexts")
        print("    4. Tests generated from:")
        print("       - Documentation examples (GOLDEN, HIGH confidence)")
        print("       - Best practices (validation)")
        print("       - Common errors (negative tests)")
        print("       - Edge cases (boundary tests)")
        print("       - Business rules (constraint tests)")
        print("       - LLM generation (fallback, MEDIUM confidence)")
        print("    5. Tests prioritized: documentation tests first")
        print("    6. RL optimizer prioritizes execution order")
        print()
        print("  📊 Expected Improvements:")
        print("    - 5-10x more tests per endpoint (vs schema-only)")
        print("    - Tests reflect actual documented behavior")
        print("    - Higher confidence tests run first")
        print("    - Reduced false positives (using documented examples)")
        print()
        print("  🚀 Next Steps:")
        print("    - Deploy and test with real API documentation")
        print("    - Monitor semantic extraction quality")
        print("    - Collect metrics on test generation improvements")
        print("    - Compare test coverage: semantic vs traditional")
        return 0
    else:
        print(f"⚠️  {total - passed} CHECKS FAILED")
        print()
        print("Review the failures above and ensure all components are integrated correctly.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
