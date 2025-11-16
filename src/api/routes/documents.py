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

        # Save file
        file_path = settings.UPLOAD_DIR / f"{doc_id}_{file.filename}"
        with open(file_path, 'wb') as f:
            f.write(contents)

        logger.info(f"File uploaded: {file.filename} ({file_size} bytes)")

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

        # Store metadata with semantic contexts
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
            # NEW: Store semantic contexts for intelligent test generation
            "semantic_contexts": parsed.get('semantic_contexts', {}),
            "semantic_summary": semantic_summary,
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
            uploaded_at=doc_metadata["uploaded_at"]
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
