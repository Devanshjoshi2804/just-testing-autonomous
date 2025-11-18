"""
Unit Tests for Workflow Orchestrator
Phase 9: Critical Infrastructure & Production Readiness
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.workflow.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowPhase,
    WorkflowResult,
    WorkflowStep
)


class TestWorkflowStep:
    """Test WorkflowStep dataclass"""

    def test_workflow_step_creation(self):
        """Test creating a workflow step"""
        step = WorkflowStep(
            phase=WorkflowPhase.DOCUMENT_PARSING,
            name="Parse document"
        )

        assert step.phase == WorkflowPhase.DOCUMENT_PARSING
        assert step.name == "Parse document"
        assert step.started_at is None
        assert step.completed_at is None
        assert step.duration == 0.0
        assert step.success is False

    def test_workflow_step_with_timing(self):
        """Test workflow step with timing information"""
        now = datetime.now()
        step = WorkflowStep(
            phase=WorkflowPhase.STORAGE,
            name="Store in RAG",
            started_at=now,
            completed_at=now,
            duration=1.5,
            success=True
        )

        assert step.duration == 1.5
        assert step.success is True


class TestWorkflowResult:
    """Test WorkflowResult dataclass"""

    def test_workflow_result_creation(self):
        """Test creating a workflow result"""
        result = WorkflowResult(
            workflow_id="test_001",
            document_id="doc_001",
            session_id="session_001",
            status=WorkflowPhase.COMPLETED,
            started_at=datetime.now(),
            completed_at=None,
            total_duration=0.0,
            steps=[]
        )

        assert result.workflow_id == "test_001"
        assert result.status == WorkflowPhase.COMPLETED
        assert result.endpoints_found == 0
        assert result.tests_generated == 0

    def test_workflow_result_with_metrics(self):
        """Test workflow result with metrics"""
        result = WorkflowResult(
            workflow_id="test_002",
            document_id="doc_002",
            session_id="session_002",
            status=WorkflowPhase.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration=10.5,
            steps=[],
            endpoints_found=5,
            tests_generated=200,
            tests_passed=180,
            tests_failed=20,
            success_rate=90.0
        )

        assert result.endpoints_found == 5
        assert result.tests_generated == 200
        assert result.tests_passed == 180
        assert result.success_rate == 90.0


class TestWorkflowOrchestrator:
    """Test WorkflowOrchestrator"""

    def test_orchestrator_initialization(self):
        """Test creating a workflow orchestrator"""
        orchestrator = WorkflowOrchestrator()

        assert orchestrator is not None
        assert isinstance(orchestrator.workflows, dict)
        assert len(orchestrator.workflows) == 0

    def test_get_workflow_status_nonexistent(self):
        """Test getting status of nonexistent workflow"""
        orchestrator = WorkflowOrchestrator()

        status = orchestrator.get_workflow_status("nonexistent")

        assert status is None

    def test_get_all_workflows_empty(self):
        """Test getting all workflows when none exist"""
        orchestrator = WorkflowOrchestrator()

        workflows = orchestrator.get_all_workflows()

        assert workflows == []

    @pytest.mark.asyncio
    async def test_execute_step_success(self):
        """Test executing a successful workflow step"""
        orchestrator = WorkflowOrchestrator()

        workflow = WorkflowResult(
            workflow_id="test_003",
            document_id="doc_003",
            session_id="session_003",
            status=WorkflowPhase.DOCUMENT_PARSING,
            started_at=datetime.now(),
            completed_at=None,
            total_duration=0.0,
            steps=[]
        )

        async def mock_function():
            return {"result": "success"}

        step = await orchestrator._execute_step(
            workflow,
            WorkflowPhase.DOCUMENT_PARSING,
            "Test step",
            mock_function
        )

        assert step.success is True
        assert step.duration >= 0
        assert step.metadata["result"] == "success"
        assert len(workflow.steps) == 1

    @pytest.mark.asyncio
    async def test_execute_step_failure(self):
        """Test executing a failed workflow step"""
        orchestrator = WorkflowOrchestrator()

        workflow = WorkflowResult(
            workflow_id="test_004",
            document_id="doc_004",
            session_id="session_004",
            status=WorkflowPhase.DOCUMENT_PARSING,
            started_at=datetime.now(),
            completed_at=None,
            total_duration=0.0,
            steps=[]
        )

        async def mock_function_that_fails():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await orchestrator._execute_step(
                workflow,
                WorkflowPhase.DOCUMENT_PARSING,
                "Test step that fails",
                mock_function_that_fails
            )

        assert len(workflow.steps) == 1
        assert workflow.steps[0].success is False
        assert workflow.steps[0].error == "Test error"

    @pytest.mark.asyncio
    async def test_parse_document_phase(self):
        """Test document parsing phase"""
        orchestrator = WorkflowOrchestrator()

        # Create a mock document
        with patch('src.workflow.workflow_orchestrator.EnhancedDocumentParser') as mock_parser_class:
            with patch('src.workflow.workflow_orchestrator.EndpointAnalyzer') as mock_analyzer_class:
                # Setup mocks
                mock_parser = Mock()
                mock_parser.parse.return_value = {
                    'raw_text': 'Test documentation',
                    'semantic_summary': {}
                }
                mock_parser_class.return_value = mock_parser

                mock_analyzer = Mock()
                mock_analyzer.analyze_documentation.return_value = {
                    'endpoints': [{'path': '/test', 'method': 'GET'}],
                    'base_url': 'https://api.example.com'
                }
                mock_analyzer_class.return_value = mock_analyzer

                # Execute phase
                result = await orchestrator._parse_document(Path("/fake/path.json"))

                # Verify results
                assert 'parsed_data' in result
                assert 'endpoints' in result
                assert len(result['endpoints']) == 1

    @pytest.mark.asyncio
    async def test_store_in_rag_phase(self):
        """Test RAG storage phase"""
        orchestrator = WorkflowOrchestrator()

        parsed_data = {
            'raw_text': 'Test documentation text',
            'semantic_summary': {'overall_quality': 'HIGH'}
        }

        with patch('src.workflow.workflow_orchestrator.DocumentChunker') as mock_chunker_class:
            with patch('src.workflow.workflow_orchestrator.DocumentStore') as mock_store_class:
                # Setup mocks
                mock_chunker = Mock()
                mock_chunker.chunk_text.return_value = [
                    {
                        'text': 'chunk1',
                        'metadata': {}
                    },
                    {
                        'text': 'chunk2',
                        'metadata': {}
                    }
                ]
                mock_chunker_class.return_value = mock_chunker

                mock_store = Mock()
                mock_store.add_documents.return_value = None
                mock_store_class.return_value = mock_store

                # Execute phase
                result = await orchestrator._store_in_rag("doc_test", parsed_data)

                # Verify results
                assert result['chunks_created'] == 2
                mock_store.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_status_tracking(self):
        """Test that workflow status is properly tracked"""
        orchestrator = WorkflowOrchestrator()

        workflow_id = "test_005"

        # Create a minimal workflow
        workflow = WorkflowResult(
            workflow_id=workflow_id,
            document_id="doc_005",
            session_id="session_005",
            status=WorkflowPhase.DOCUMENT_PARSING,
            started_at=datetime.now(),
            completed_at=None,
            total_duration=0.0,
            steps=[]
        )

        # Store workflow
        orchestrator.workflows[workflow_id] = workflow

        # Retrieve workflow
        retrieved = orchestrator.get_workflow_status(workflow_id)

        assert retrieved is not None
        assert retrieved.workflow_id == workflow_id
        assert retrieved.status == WorkflowPhase.DOCUMENT_PARSING

    def test_workflow_phases_enum(self):
        """Test WorkflowPhase enum values"""
        assert WorkflowPhase.DOCUMENT_UPLOAD == "document_upload"
        assert WorkflowPhase.DOCUMENT_PARSING == "document_parsing"
        assert WorkflowPhase.STORAGE == "storage"
        assert WorkflowPhase.ANALYSIS == "analysis"
        assert WorkflowPhase.DEPENDENCY_GRAPH == "dependency_graph"
        assert WorkflowPhase.WORKFLOW_GENERATION == "workflow_generation"
        assert WorkflowPhase.TEST_GENERATION == "test_generation"
        assert WorkflowPhase.TEST_EXECUTION == "test_execution"
        assert WorkflowPhase.REPORTING == "reporting"
        assert WorkflowPhase.COMPLETED == "completed"
        assert WorkflowPhase.FAILED == "failed"
