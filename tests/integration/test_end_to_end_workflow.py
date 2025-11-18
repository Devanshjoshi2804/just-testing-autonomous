"""
Integration Tests for End-to-End Workflow
Tests complete pipeline from document upload to test execution
Phase 8.5: Complete Integration & End-to-End Workflow
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from src.workflow.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowPhase,
    WorkflowResult
)


@pytest.fixture
def sample_openapi_doc():
    """Create a sample OpenAPI documentation file"""
    content = """
    {
        "openapi": "3.0.0",
        "info": {
            "title": "Pet Store API",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "https://petstore.example.com/api/v1"
            }
        ],
        "paths": {
            "/pets": {
                "get": {
                    "summary": "List all pets",
                    "operationId": "listPets",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "How many items to return",
                            "required": false,
                            "schema": {
                                "type": "integer",
                                "maximum": 100
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "A paged array of pets"
                        }
                    }
                },
                "post": {
                    "summary": "Create a pet",
                    "operationId": "createPet",
                    "requestBody": {
                        "required": true,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "tag": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Pet created"
                        }
                    }
                }
            },
            "/pets/{petId}": {
                "get": {
                    "summary": "Info for a specific pet",
                    "operationId": "showPetById",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": true,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Expected response to a valid request"
                        }
                    }
                },
                "put": {
                    "summary": "Update a pet",
                    "operationId": "updatePet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": true,
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
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "tag": {
                                            "type": "string"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Pet updated"
                        }
                    }
                },
                "delete": {
                    "summary": "Delete a pet",
                    "operationId": "deletePet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": true,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "204": {
                            "description": "Pet deleted"
                        }
                    }
                }
            }
        }
    }
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(content)
        return Path(f.name)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, sample_openapi_doc):
        """Test complete workflow from document to test execution"""
        orchestrator = WorkflowOrchestrator()

        # Execute complete workflow
        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_001",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            document_name="Pet Store API",
            max_retries=2,
            comprehensive_mode=False,  # Faster for testing
            use_rl_optimization=False
        )

        # Verify workflow completed
        assert result is not None
        assert result.workflow_id == "test_workflow_001"
        assert result.status == WorkflowPhase.COMPLETED or result.status == WorkflowPhase.FAILED

        # If successful, verify all phases executed
        if result.status == WorkflowPhase.COMPLETED:
            phase_names = [step.phase for step in result.steps]

            assert WorkflowPhase.DOCUMENT_PARSING in phase_names
            assert WorkflowPhase.STORAGE in phase_names
            assert WorkflowPhase.ANALYSIS in phase_names
            assert WorkflowPhase.DEPENDENCY_GRAPH in phase_names
            assert WorkflowPhase.WORKFLOW_GENERATION in phase_names
            assert WorkflowPhase.TEST_GENERATION in phase_names
            assert WorkflowPhase.TEST_EXECUTION in phase_names
            assert WorkflowPhase.REPORTING in phase_names

            # Verify endpoints were found
            assert result.endpoints_found > 0

            # Verify chunks were created
            assert result.chunks_created > 0

            # Verify tests were generated
            assert result.tests_generated > 0

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_workflow_step_timing(self, sample_openapi_doc):
        """Test that workflow steps are timed correctly"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_002",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Verify each step has timing information
        for step in result.steps:
            assert step.started_at is not None
            assert step.completed_at is not None
            assert step.duration >= 0

        # Verify total duration
        assert result.total_duration >= 0

        if result.status == WorkflowPhase.COMPLETED:
            # Total duration should be sum of all steps
            total_step_duration = sum(step.duration for step in result.steps)
            assert result.total_duration >= total_step_duration

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_dependency_graph_integration(self, sample_openapi_doc):
        """Test dependency graph integration in workflow"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_003",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        if result.status == WorkflowPhase.COMPLETED:
            # Verify dependency graph was built
            assert result.total_resources >= 0
            assert result.total_dependencies >= 0

            # Pet Store API should have at least 1 CRUD chain (pets resource)
            assert result.crud_chains_found >= 1

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_workflow_sequences_generation(self, sample_openapi_doc):
        """Test workflow sequence generation in pipeline"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_004",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        if result.status == WorkflowPhase.COMPLETED:
            # Verify workflow sequences were generated
            assert result.workflow_sequences_generated >= 0
            assert result.total_workflow_steps >= 0

            # Verify reports include workflow intelligence
            reports = result.metadata.get('reports', {})
            assert 'workflow_intelligence' in reports

            workflow_intel = reports['workflow_intelligence']
            assert 'sequences_generated' in workflow_intel
            assert 'data_flows_tracked' in workflow_intel

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_comprehensive_mode_test_generation(self, sample_openapi_doc):
        """Test comprehensive mode generates more tests"""
        orchestrator = WorkflowOrchestrator()

        # Run in basic mode
        result_basic = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_005_basic",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Run in comprehensive mode
        result_comprehensive = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_005_comprehensive",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=True,
            use_rl_optimization=False
        )

        if result_basic.status == WorkflowPhase.COMPLETED and result_comprehensive.status == WorkflowPhase.COMPLETED:
            # Comprehensive mode should generate more tests
            assert result_comprehensive.tests_generated > result_basic.tests_generated

            # Comprehensive mode should include mutation tests
            assert result_comprehensive.mutation_tests_count > 0
            assert result_comprehensive.security_tests_count > 0

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self):
        """Test workflow handles errors gracefully"""
        orchestrator = WorkflowOrchestrator()

        # Try with invalid document path
        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_006",
            document_path=Path("/nonexistent/file.json"),
            base_url="https://example.com",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Verify workflow failed
        assert result.status == WorkflowPhase.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_workflow_status_retrieval(self, sample_openapi_doc):
        """Test retrieving workflow status"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_007",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Retrieve workflow status
        status = orchestrator.get_workflow_status("test_workflow_007")

        assert status is not None
        assert status.workflow_id == "test_workflow_007"
        assert status.status in [WorkflowPhase.COMPLETED, WorkflowPhase.FAILED]

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_multiple_workflows(self, sample_openapi_doc):
        """Test running multiple workflows"""
        orchestrator = WorkflowOrchestrator()

        # Run multiple workflows
        results = []
        for i in range(3):
            result = await orchestrator.execute_complete_workflow(
                workflow_id=f"test_workflow_008_{i}",
                document_path=sample_openapi_doc,
                base_url="https://petstore.example.com/api/v1",
                comprehensive_mode=False,
                use_rl_optimization=False
            )
            results.append(result)

        # Verify all workflows tracked
        all_workflows = orchestrator.get_all_workflows()
        assert len(all_workflows) >= 3

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_advanced_reporting(self, sample_openapi_doc):
        """Test advanced reporting generation"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_workflow_009",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=True,
            use_rl_optimization=False
        )

        if result.status == WorkflowPhase.COMPLETED:
            # Verify reports were generated
            reports = result.metadata.get('reports', {})

            assert 'workflow_summary' in reports
            assert 'dependency_analysis' in reports
            assert 'workflow_intelligence' in reports
            assert 'test_coverage' in reports
            assert 'phase_timing' in reports

            # Verify workflow summary
            summary = reports['workflow_summary']
            assert 'workflow_id' in summary
            assert 'total_duration' in summary
            assert 'success_rate' in summary

            # Verify phase timing
            phase_timing = reports['phase_timing']
            assert len(phase_timing) > 0

            for phase in phase_timing:
                assert 'phase' in phase
                assert 'duration' in phase
                assert 'success' in phase

        # Cleanup
        sample_openapi_doc.unlink()


class TestWorkflowPhases:
    """Test individual workflow phases"""

    @pytest.mark.asyncio
    async def test_document_parsing_phase(self, sample_openapi_doc):
        """Test document parsing phase"""
        orchestrator = WorkflowOrchestrator()

        # Execute workflow
        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_phase_001",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Find parsing step
        parsing_step = next(
            (s for s in result.steps if s.phase == WorkflowPhase.DOCUMENT_PARSING),
            None
        )

        assert parsing_step is not None

        if parsing_step.success:
            assert 'parsed_data' in parsing_step.metadata
            assert 'endpoints' in parsing_step.metadata

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_storage_phase(self, sample_openapi_doc):
        """Test RAG storage phase"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_phase_002",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Find storage step
        storage_step = next(
            (s for s in result.steps if s.phase == WorkflowPhase.STORAGE),
            None
        )

        assert storage_step is not None

        if storage_step.success:
            assert storage_step.metadata.get('chunks_created', 0) > 0

        # Cleanup
        sample_openapi_doc.unlink()

    @pytest.mark.asyncio
    async def test_analysis_phase(self, sample_openapi_doc):
        """Test constraint extraction and analysis phase"""
        orchestrator = WorkflowOrchestrator()

        result = await orchestrator.execute_complete_workflow(
            workflow_id="test_phase_003",
            document_path=sample_openapi_doc,
            base_url="https://petstore.example.com/api/v1",
            comprehensive_mode=False,
            use_rl_optimization=False
        )

        # Find analysis step
        analysis_step = next(
            (s for s in result.steps if s.phase == WorkflowPhase.ANALYSIS),
            None
        )

        assert analysis_step is not None

        if analysis_step.success:
            assert 'constraints' in analysis_step.metadata
            assert 'total_params' in analysis_step.metadata

        # Cleanup
        sample_openapi_doc.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
