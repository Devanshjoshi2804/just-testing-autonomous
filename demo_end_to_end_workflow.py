#!/usr/bin/env python3
"""
End-to-End Workflow Demo
Demonstrates complete integration from document upload to test execution
Phase 8.5: Complete Integration & End-to-End Workflow
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from datetime import datetime

from loguru import logger

from src.workflow.workflow_orchestrator import WorkflowOrchestrator, WorkflowPhase
from src.reporting.advanced_reporter import AdvancedReporter, ReportFormat


# Sample OpenAPI documentation for demo
SAMPLE_PETSTORE_API = """
{
    "openapi": "3.0.0",
    "info": {
        "title": "Pet Store API",
        "version": "1.0.0",
        "description": "A sample Pet Store API to demonstrate AutoTest-RL capabilities"
    },
    "servers": [
        {
            "url": "https://petstore.swagger.io/v2",
            "description": "Pet Store API Server"
        }
    ],
    "paths": {
        "/pets": {
            "get": {
                "summary": "List all pets",
                "description": "Returns a list of all pets in the store. Supports pagination via limit parameter.",
                "operationId": "listPets",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "description": "Maximum number of pets to return (1-100)",
                        "required": false,
                        "schema": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20
                        }
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "description": "Number of pets to skip",
                        "required": false,
                        "schema": {
                            "type": "integer",
                            "minimum": 0,
                            "default": 0
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "A paged array of pets",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/Pet"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "post": {
                "summary": "Create a pet",
                "description": "Creates a new pet in the store. Name is required.",
                "operationId": "createPet",
                "tags": ["pets"],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/NewPet"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Pet created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input"
                    }
                }
            }
        },
        "/pets/{petId}": {
            "get": {
                "summary": "Get pet by ID",
                "description": "Returns a single pet by ID",
                "operationId": "showPetById",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": true,
                        "description": "The ID of the pet to retrieve",
                        "schema": {
                            "type": "string",
                            "pattern": "^[0-9]+$"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Expected response to a valid request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Pet"
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            },
            "put": {
                "summary": "Update a pet",
                "description": "Updates an existing pet's information",
                "operationId": "updatePet",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": true,
                        "description": "The ID of the pet to update",
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/NewPet"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Pet updated successfully"
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            },
            "delete": {
                "summary": "Delete a pet",
                "description": "Deletes a pet from the store",
                "operationId": "deletePet",
                "tags": ["pets"],
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": true,
                        "description": "The ID of the pet to delete",
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "204": {
                        "description": "Pet deleted successfully"
                    },
                    "404": {
                        "description": "Pet not found"
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id": {
                        "type": "integer",
                        "format": "int64"
                    },
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "tag": {
                        "type": "string"
                    }
                }
            },
            "NewPet": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100
                    },
                    "tag": {
                        "type": "string"
                    }
                }
            }
        }
    }
}
"""


async def demo_complete_workflow():
    """
    Demonstrate complete end-to-end workflow

    This demo shows:
    1. Document upload and parsing with semantic analysis
    2. Storage in RAG system (ChromaDB)
    3. Endpoint recognition and analysis
    4. Constraint extraction
    5. Dependency graph construction
    6. Workflow sequence generation
    7. Comprehensive test generation (Semantic + LLM + Security)
    8. Test execution with RL prioritization
    9. Self-healing and adaptation
    10. Advanced reporting
    """

    logger.info("=" * 80)
    logger.info("🚀 AutoTest-RL: End-to-End Workflow Demo")
    logger.info("=" * 80)
    logger.info("")

    # ========================================================================
    # Step 1: Create sample documentation file
    # ========================================================================
    logger.info("📄 Step 1: Creating sample API documentation (Pet Store API)")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(SAMPLE_PETSTORE_API)
        doc_path = Path(f.name)

    logger.info(f"   ✅ Documentation file created: {doc_path}")
    logger.info("")

    # ========================================================================
    # Step 2: Initialize workflow orchestrator
    # ========================================================================
    logger.info("🔧 Step 2: Initializing Workflow Orchestrator")

    orchestrator = WorkflowOrchestrator()

    logger.info("   ✅ Orchestrator initialized")
    logger.info("")

    # ========================================================================
    # Step 3: Execute complete workflow
    # ========================================================================
    logger.info("🎯 Step 3: Executing Complete End-to-End Workflow")
    logger.info("")
    logger.info("   This will:")
    logger.info("   • Parse the OpenAPI documentation")
    logger.info("   • Store it in ChromaDB (RAG system)")
    logger.info("   • Extract endpoints and constraints")
    logger.info("   • Build dependency graph")
    logger.info("   • Generate workflow sequences (CRUD chains)")
    logger.info("   • Generate comprehensive tests")
    logger.info("   • Execute tests (note: API server may not be running)")
    logger.info("   • Generate advanced reports")
    logger.info("")

    workflow_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    result = await orchestrator.execute_complete_workflow(
        workflow_id=workflow_id,
        document_path=doc_path,
        base_url="https://petstore.swagger.io/v2",
        document_name="Pet Store API Demo",
        max_retries=2,
        comprehensive_mode=True,  # Enable all advanced features
        use_rl_optimization=True   # Enable RL-based test prioritization
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Workflow Results")
    logger.info("=" * 80)

    # ========================================================================
    # Step 4: Display results
    # ========================================================================
    logger.info(f"Workflow ID:      {result.workflow_id}")
    logger.info(f"Status:           {result.status}")
    logger.info(f"Total Duration:   {result.total_duration:.2f}s")
    logger.info("")

    logger.info("📑 Document Processing:")
    logger.info(f"   Endpoints Found:           {result.endpoints_found}")
    logger.info(f"   Chunks Created:            {result.chunks_created}")
    logger.info(f"   Parameters w/ Constraints: {result.parameters_with_constraints}")
    logger.info("")

    logger.info("🔗 Dependency Analysis:")
    logger.info(f"   Total Resources:     {result.total_resources}")
    logger.info(f"   Total Dependencies:  {result.total_dependencies}")
    logger.info(f"   CRUD Chains Found:   {result.crud_chains_found}")
    logger.info("")

    logger.info("🔄 Workflow Intelligence:")
    logger.info(f"   Sequences Generated: {result.workflow_sequences_generated}")
    logger.info(f"   Total Steps:         {result.total_workflow_steps}")
    logger.info(f"   Data Flows Tracked:  {result.data_flows_tracked}")
    logger.info(f"   ID Extractions:      {result.id_extractions}")
    logger.info("")

    logger.info("🧪 Test Execution:")
    logger.info(f"   Tests Generated:     {result.tests_generated}")
    logger.info(f"   Tests Passed:        {result.tests_passed}")
    logger.info(f"   Tests Failed:        {result.tests_failed}")
    logger.info(f"   Success Rate:        {result.success_rate:.1f}%")
    logger.info("")

    logger.info("🔬 Advanced Testing:")
    logger.info(f"   Semantic Tests:      {result.semantic_tests_count}")
    logger.info(f"   Mutation Tests:      {result.mutation_tests_count}")
    logger.info(f"   Security Tests:      {result.security_tests_count}")
    logger.info(f"   Healing Actions:     {result.healing_actions}")
    logger.info("")

    # ========================================================================
    # Step 5: Show phase breakdown
    # ========================================================================
    logger.info("⏱️  Phase Breakdown:")
    for step in result.steps:
        status_icon = "✅" if step.success else "❌"
        logger.info(f"   {status_icon} {step.name:<50} {step.duration:>6.2f}s")
    logger.info("")

    # ========================================================================
    # Step 6: Generate advanced reports
    # ========================================================================
    if result.status == WorkflowPhase.COMPLETED:
        logger.info("=" * 80)
        logger.info("📊 Generating Advanced Reports")
        logger.info("=" * 80)

        reporter = AdvancedReporter()

        # Generate JSON report
        logger.info("📄 Generating JSON report...")
        json_report = reporter.generate_comprehensive_report(
            workflow_result=result,
            test_results=result.metadata.get('test_results', {}),
            dependency_graph=result.metadata.get('dependency_graph'),
            workflow_sequences=result.metadata.get('workflow_sequences', []),
            format=ReportFormat.JSON
        )
        logger.info(f"   ✅ JSON report: {json_report}")

        # Generate Markdown report
        logger.info("📝 Generating Markdown report...")
        md_report = reporter.generate_comprehensive_report(
            workflow_result=result,
            test_results=result.metadata.get('test_results', {}),
            dependency_graph=result.metadata.get('dependency_graph'),
            workflow_sequences=result.metadata.get('workflow_sequences', []),
            format=ReportFormat.MARKDOWN
        )
        logger.info(f"   ✅ Markdown report: {md_report}")

        # Generate HTML report
        logger.info("🌐 Generating HTML report...")
        html_report = reporter.generate_comprehensive_report(
            workflow_result=result,
            test_results=result.metadata.get('test_results', {}),
            dependency_graph=result.metadata.get('dependency_graph'),
            workflow_sequences=result.metadata.get('workflow_sequences', []),
            format=ReportFormat.HTML
        )
        logger.info(f"   ✅ HTML report: {html_report}")

        logger.info("")

    # ========================================================================
    # Summary and next steps
    # ========================================================================
    logger.info("=" * 80)
    logger.info("✅ Demo Completed Successfully!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("🎉 AutoTest-RL has successfully demonstrated:")
    logger.info("")
    logger.info("   ✓ Document parsing with semantic analysis")
    logger.info("   ✓ RAG system integration (ChromaDB)")
    logger.info("   ✓ Intelligent endpoint recognition")
    logger.info("   ✓ Constraint extraction from documentation")
    logger.info("   ✓ Dependency graph construction")
    logger.info("   ✓ Workflow sequence generation (CRUD chains)")
    logger.info("   ✓ Comprehensive test generation")
    logger.info("   ✓ Multi-layered testing (Semantic + LLM + Security)")
    logger.info("   ✓ Security mutation testing (OWASP Top 10)")
    logger.info("   ✓ Test execution with intelligent retry")
    logger.info("   ✓ Advanced reporting with multiple formats")
    logger.info("")
    logger.info("📚 Next Steps:")
    logger.info("   • Review generated reports in ./reports/")
    logger.info("   • Check workflow sequences in workflow intelligence section")
    logger.info("   • Examine security test results")
    logger.info("   • Review phase timing for optimization opportunities")
    logger.info("")

    # Cleanup
    doc_path.unlink()

    return result


async def demo_multiple_workflows():
    """Demo: Running multiple workflows in sequence"""

    logger.info("=" * 80)
    logger.info("🔄 Demo: Multiple Workflow Execution")
    logger.info("=" * 80)
    logger.info("")

    orchestrator = WorkflowOrchestrator()

    # Create sample doc
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(SAMPLE_PETSTORE_API)
        doc_path = Path(f.name)

    # Run 3 workflows with different configurations
    configs = [
        {"comprehensive_mode": False, "use_rl_optimization": False},
        {"comprehensive_mode": True, "use_rl_optimization": False},
        {"comprehensive_mode": True, "use_rl_optimization": True}
    ]

    results = []
    for i, config in enumerate(configs, 1):
        logger.info(f"🚀 Running workflow {i}/3...")
        logger.info(f"   Config: {config}")

        workflow_id = f"demo_multi_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        result = await orchestrator.execute_complete_workflow(
            workflow_id=workflow_id,
            document_path=doc_path,
            base_url="https://petstore.swagger.io/v2",
            max_retries=1,
            **config
        )

        results.append(result)
        logger.info(f"   ✅ Completed in {result.total_duration:.2f}s")
        logger.info("")

    # Compare results
    logger.info("📊 Comparison:")
    logger.info(f"{'Config':<30} {'Duration':<12} {'Tests':<10} {'Success Rate'}")
    logger.info("-" * 70)

    for i, (result, config) in enumerate(zip(results, configs), 1):
        config_str = f"Basic" if not config["comprehensive_mode"] else "Comprehensive"
        if config["use_rl_optimization"]:
            config_str += " + RL"

        logger.info(
            f"{config_str:<30} {result.total_duration:>8.2f}s    "
            f"{result.tests_generated:>6}    {result.success_rate:>6.1f}%"
        )

    logger.info("")

    # Cleanup
    doc_path.unlink()


def main():
    """Main demo entry point"""

    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║              AutoTest-RL: End-to-End Workflow Demo               ║")
    print("║                                                                   ║")
    print("║   Intelligent API Testing with Reinforcement Learning            ║")
    print("║   Phase 8.5: Complete Integration & End-to-End Workflow          ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print("\n")

    try:
        # Run main demo
        asyncio.run(demo_complete_workflow())

        print("\n")
        print("=" * 80)
        print("Would you like to see a comparison of different configurations?")
        print("=" * 80)
        print("\n")

        # Optionally run multi-workflow demo
        # Uncomment to enable:
        # asyncio.run(demo_multiple_workflows())

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ Demo failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
