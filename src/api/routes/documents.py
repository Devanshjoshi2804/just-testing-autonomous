"""
Document Management Routes
Upload, list, and retrieve API documentation
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from loguru import logger

from src.config import settings
from src.models import (
    DocumentUploadResponse,
    DocumentListResponse,
    ErrorResponse,
    EndpointInfo
)
from src.parsers.document_parser import DocumentParser
from src.parsers.enhanced_document_parser import EnhancedDocumentParser
from src.parsers.text_splitter import DocumentChunker
from src.rag.doc_store import DocumentStore
from src.agents.endpoint_analyzer import EndpointAnalyzer
from src.analysis.constraint_extractor import ConstraintExtractor
from src.workflow.dependency_graph import DependencyGraph
from src.workflow.state_transition_tester import StateTransitionTester


router = APIRouter()

# In-memory storage for demo (use database in production)
documents_db = {}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Upload API Documentation",
    description="Upload PDF, JSON, or YAML API documentation for analysis and testing"
)
async def upload_document(
    file: UploadFile = File(..., description="API documentation file"),
    name: str = Form(None, description="Document name"),
    description: str = Form(None, description="Document description"),
    base_url: str = Form(None, description="API base URL (optional)")
):
    """
    Upload API documentation file

    Accepts PDF, JSON, or YAML files containing API documentation.
    The system will:
    1. Parse the document
    2. Extract text and chunk it
    3. Store in ChromaDB for RAG
    4. Analyze endpoints using AI
    5. Return document ID for testing
    """
    try:
        # Validate file type
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. "
                       f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )

        # Validate file size
        file_size = 0
        contents = await file.read()
        file_size = len(contents)

        if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Generate unique document ID
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        # SECURITY: Sanitize filename to prevent path traversal attacks
        # Remove path components (../, /, \, etc.) from user-supplied filename
        safe_filename = Path(file.filename).name
        if not safe_filename:
            # If filename becomes empty after sanitization, use a generic name
            safe_filename = f"document.{file_ext}"

        # Additional security: Remove any remaining dangerous characters
        safe_filename = safe_filename.replace('\x00', '').strip()

        # Save file with sanitized name
        file_path = settings.UPLOAD_DIR / f"{doc_id}_{safe_filename}"

        # Ensure the final path is still within the upload directory
        file_path = file_path.resolve()
        upload_dir_resolved = settings.UPLOAD_DIR.resolve()

        if not str(file_path).startswith(str(upload_dir_resolved)):
            logger.error(f"Security: Path traversal attempt detected! File: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid filename detected. Path traversal attempts are blocked."
            )

        # Save file securely
        with open(file_path, 'wb') as f:
            f.write(contents)

        logger.info(f"File uploaded securely: {safe_filename} ({file_size} bytes) -> {doc_id}")

        # Parse document with semantic analysis
        logger.info("🧠 Parsing document with semantic analysis...")
        enhanced_parser = EnhancedDocumentParser(enable_semantic_analysis=True)
        parsed = enhanced_parser.parse(file_path)

        # Extract base URL if not provided
        if not base_url:
            base_url = DocumentParser().extract_base_url(parsed)

        # Chunk text
        chunker = DocumentChunker()
        chunks = chunker.chunk_text(parsed['raw_text'])

        # Store in ChromaDB with semantic metadata
        doc_store = DocumentStore(collection_name=f"doc_{doc_id}")

        # Add semantic context to chunk metadata if available
        semantic_summary = parsed.get('semantic_summary', {})
        for chunk in chunks:
            chunk['metadata']['semantic_quality'] = semantic_summary.get('overall_quality', 'UNKNOWN')
            chunk['metadata']['has_semantic_context'] = semantic_summary.get('endpoints_with_context', 0) > 0

        doc_store.add_documents(chunks)

        logger.info(f"Created {len(chunks)} chunks in ChromaDB")

        # Log semantic analysis results
        if semantic_summary:
            logger.info(
                f"📚 Semantic Analysis: {semantic_summary.get('endpoints_with_context', 0)} endpoints "
                f"with {semantic_summary.get('total_examples', 0)} examples, "
                f"{semantic_summary.get('total_best_practices', 0)} best practices, "
                f"{semantic_summary.get('total_common_errors', 0)} error scenarios"
            )

        # Analyze endpoints with AI
        analyzer = EndpointAnalyzer()
        analysis = analyzer.analyze_documentation(
            doc_text=parsed['raw_text'],
            base_url=base_url
        )

        endpoints = analysis.get('endpoints', [])
        extracted_base_url = analysis.get('base_url') or base_url

        logger.info(f"Found {len(endpoints)} endpoints")

        # Extract constraints for all endpoints
        logger.info("🔍 Extracting parameter constraints...")
        constraint_extractor = ConstraintExtractor()
        endpoint_constraints = {}

        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method', 'GET')} {endpoint.get('path', '')}"

            # Extract constraints from endpoint definition + documentation
            constraints = constraint_extractor.extract_constraints(
                endpoint=endpoint,
                documentation=parsed['raw_text']
            )

            endpoint_constraints[endpoint_key] = constraints

            # Log what we found
            params_with_constraints = sum(
                1 for c in constraints.values() if c.constraints
            )
            if params_with_constraints > 0:
                logger.info(
                    f"  {endpoint_key}: {params_with_constraints}/{len(constraints)} "
                    f"params with constraints"
                )

        # Get constraint extraction summary
        total_params = sum(len(c) for c in endpoint_constraints.values())
        total_with_constraints = sum(
            sum(1 for param in c.values() if param.constraints)
            for c in endpoint_constraints.values()
        )

        logger.info(
            f"✅ Constraint extraction complete: {total_with_constraints}/{total_params} "
            f"params have constraints ({total_with_constraints/total_params*100 if total_params > 0 else 0:.1f}%)"
        )

        # Build dependency graph for workflow intelligence
        logger.info("🔗 Building endpoint dependency graph...")
        dependency_graph = DependencyGraph()
        dependency_graph.build_graph(endpoints)

        # Get graph summary
        graph_summary = dependency_graph.get_graph_summary()
        logger.info(
            f"✅ Dependency graph built: {graph_summary['total_resources']} resources, "
            f"{graph_summary['total_dependencies']} dependencies, "
            f"{graph_summary['crud_resource_count']} complete CRUD chains"
        )

        # Convert dependencies to serializable format
        serializable_dependencies = [
            {
                'source': dep.source_endpoint,
                'target': dep.target_endpoint,
                'type': dep.dependency_type,
                'shared_resource': dep.shared_resource,
                'confidence': dep.confidence,
                'description': dep.description
            }
            for dep in dependency_graph.dependencies
        ]

        # Convert resources to serializable format
        serializable_resources = {
            name: {
                'resource_name': res.resource_name,
                'base_path': res.base_path,
                'create_endpoint': res.create_endpoint,
                'read_list_endpoint': res.read_list_endpoint,
                'read_single_endpoint': res.read_single_endpoint,
                'update_endpoint': res.update_endpoint,
                'delete_endpoint': res.delete_endpoint,
                'child_resources': res.child_resources,
                'parent_resource': res.parent_resource
            }
            for name, res in dependency_graph.resources.items()
        }

        # Generate workflow sequences for state transition testing
        logger.info("🔄 Generating workflow sequences for state transition testing...")
        state_tester = StateTransitionTester(dependency_graph)
        workflow_sequences = state_tester.generate_workflow_sequences()

        # Get workflow summary
        workflow_summary = state_tester.get_workflow_summary()
        logger.info(
            f"✅ Workflow sequences generated: {workflow_summary['total_workflows']} workflows, "
            f"{workflow_summary['total_steps']} total steps, "
            f"{workflow_summary['resource_count']} resources with workflows"
        )

        # Convert workflows to serializable format
        serializable_workflows = [
            {
                'resource_name': wf.resource_name,
                'sequence_name': wf.sequence_name,
                'description': wf.description,
                'expected_outcome': wf.expected_outcome,
                'steps': wf.steps
            }
            for wf in workflow_sequences
        ]

        # Convert constraints to serializable format
        serializable_constraints = {}
        for endpoint_key, constraints_map in endpoint_constraints.items():
            serializable_constraints[endpoint_key] = {
                param_name: {
                    'name': param_constraints.name,
                    'type': param_constraints.type,
                    'required': param_constraints.required,
                    'description': param_constraints.description,
                    'example_values': param_constraints.example_values,
                    'constraints': [
                        {
                            'type': c.constraint_type,
                            'value': c.value,
                            'description': c.description,
                            'confidence': c.confidence
                        }
                        for c in param_constraints.constraints
                    ]
                }
                for param_name, param_constraints in constraints_map.items()
            }

        # Store metadata with semantic contexts and constraints
        doc_metadata = {
            "id": doc_id,
            "filename": file.filename,
            "doc_type": file_ext,
            "file_size": file_size,
            "file_path": str(file_path),
            "base_url": extracted_base_url,
            "endpoints": endpoints,
            "chunks_count": len(chunks),
            "uploaded_at": datetime.now(),
            "name": name or file.filename,
            "description": description,
            # Semantic contexts for intelligent test generation
            "semantic_contexts": parsed.get('semantic_contexts', {}),
            "semantic_summary": semantic_summary,
            # Parameter constraints for constraint-aware test data generation
            "parameter_constraints": serializable_constraints,
            "constraints_coverage": {
                "total_parameters": total_params,
                "parameters_with_constraints": total_with_constraints,
                "coverage_percentage": total_with_constraints/total_params*100 if total_params > 0 else 0
            },
            # Dependency graph for workflow intelligence
            "dependency_graph": {
                "dependencies": serializable_dependencies,
                "resources": serializable_resources,
                "summary": graph_summary
            },
            # Workflow sequences for state transition testing
            "workflow_sequences": {
                "workflows": serializable_workflows,
                "summary": workflow_summary
            }
        }
        documents_db[doc_id] = doc_metadata

        # Build response
        response = DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            doc_type=file_ext,
            file_size=file_size,
            base_url=extracted_base_url,
            endpoints_found=len(endpoints),
            chunks_created=len(chunks),
            uploaded_at=doc_metadata["uploaded_at"],
            parameters_with_constraints=total_with_constraints,
            constraints_coverage=round(total_with_constraints/total_params*100, 1) if total_params > 0 else 0
        )

        logger.info(f"✅ Document uploaded successfully: {doc_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List Documents",
    description="Get list of all uploaded documents"
)
async def list_documents():
    """List all uploaded documents"""
    try:
        docs = []
        for doc_id, metadata in documents_db.items():
            docs.append({
                "id": doc_id,
                "filename": metadata["filename"],
                "name": metadata.get("name"),
                "doc_type": metadata["doc_type"],
                "file_size": metadata["file_size"],
                "base_url": metadata.get("base_url"),
                "endpoints_count": len(metadata.get("endpoints", [])),
                "uploaded_at": metadata["uploaded_at"].isoformat()
            })

        return DocumentListResponse(
            documents=sorted(docs, key=lambda x: x["uploaded_at"], reverse=True),
            total=len(docs)
        )

    except Exception as e:
        logger.error(f"List documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_id}",
    summary="Get Document Details",
    description="Get detailed information about a specific document"
)
async def get_document(document_id: str):
    """Get document details including endpoints"""
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        metadata = documents_db[document_id]

        # Convert endpoints to response model
        endpoints = [
            EndpointInfo(
                path=ep.get("path", ""),
                method=ep.get("method", "GET"),
                summary=ep.get("summary"),
                auth_required=ep.get("auth_required", False),
                parameters=ep.get("parameters", [])
            )
            for ep in metadata.get("endpoints", [])
        ]

        return {
            "id": document_id,
            "filename": metadata["filename"],
            "name": metadata.get("name"),
            "description": metadata.get("description"),
            "doc_type": metadata["doc_type"],
            "file_size": metadata["file_size"],
            "base_url": metadata.get("base_url"),
            "endpoints": endpoints,
            "chunks_count": metadata["chunks_count"],
            "uploaded_at": metadata["uploaded_at"].isoformat(),
        }

    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{document_id}",
    summary="Delete Document",
    description="Delete a document and its associated data"
)
async def delete_document(document_id: str):
    """Delete document and cleanup"""
    if document_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        metadata = documents_db[document_id]

        # Delete file
        file_path = Path(metadata["file_path"])
        if file_path.exists():
            file_path.unlink()

        # Delete ChromaDB collection
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")
        doc_store.delete_collection()

        # Remove from DB
        del documents_db[document_id]

        logger.info(f"✅ Document deleted: {document_id}")

        return {"message": "Document deleted successfully", "document_id": document_id}

    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
