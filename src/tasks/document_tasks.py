"""
Document Processing Celery Tasks
Background tasks for document upload, parsing, and analysis
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from celery import Task
from loguru import logger
from typing import Dict, Any
import time

from src.tasks.celery_app import celery_app
from src.parsers.document_parser import DocumentParser
from src.parsers.text_splitter import DocumentChunker
from src.rag.doc_store import DocumentStore
from src.agents.endpoint_analyzer import EndpointAnalyzer


class CallbackTask(Task):
    """Base task class with progress callbacks"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"✅ Task {task_id} succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"❌ Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry"""
        logger.warning(f"🔄 Task {task_id} retrying: {exc}")


@celery_app.task(
    name="process_document",
    base=CallbackTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_document_task(
    self,
    document_id: str,
    file_path: str,
    base_url: str = None,
) -> Dict[str, Any]:
    """
    Background task to process uploaded document

    This task:
    1. Parses the document (PDF/JSON/YAML)
    2. Validates it contains API documentation
    3. Chunks the text for RAG
    4. Stores chunks in ChromaDB
    5. Analyzes endpoints using AI
    6. Returns processing results

    Args:
        self: Celery task instance
        document_id: Unique document ID
        file_path: Path to uploaded file
        base_url: Optional base URL override

    Returns:
        dict: Processing results with endpoints and metadata
    """
    try:
        logger.info(f"📄 Processing document: {document_id} from {file_path}")

        # Update task state to PROCESSING
        self.update_state(
            state="PROCESSING",
            meta={
                "step": "parsing",
                "progress": 10,
                "message": "Parsing document...",
            },
        )

        # Step 1: Parse document
        start_time = time.time()
        parser = DocumentParser()
        parsed_data = parser.parse(file_path)

        logger.info(
            f"Parsed document: {parsed_data['doc_type']}, "
            f"{len(parsed_data['raw_text'])} chars"
        )

        # Step 2: Validate API documentation
        self.update_state(
            state="PROCESSING",
            meta={
                "step": "validating",
                "progress": 25,
                "message": "Validating API documentation...",
            },
        )

        is_valid = parser.validate_api_doc(parsed_data)
        if not is_valid:
            raise ValueError("Document does not appear to contain API documentation")

        # Step 3: Extract base URL
        if not base_url:
            base_url = parser.extract_base_url(parsed_data)

        logger.info(f"Base URL: {base_url}")

        # Step 4: Chunk text
        self.update_state(
            state="PROCESSING",
            meta={
                "step": "chunking",
                "progress": 40,
                "message": "Chunking text for RAG...",
            },
        )

        chunker = DocumentChunker()
        chunks = chunker.chunk_text(parsed_data["raw_text"])

        logger.info(f"Created {len(chunks)} text chunks")

        # Step 5: Store in ChromaDB
        self.update_state(
            state="PROCESSING",
            meta={
                "step": "storing",
                "progress": 60,
                "message": "Storing in vector database...",
            },
        )

        doc_store = DocumentStore(collection_name=f"doc_{document_id}")
        doc_store.add_documents(
            texts=chunks,
            metadatas=[
                {
                    "document_id": document_id,
                    "chunk_index": i,
                    "doc_type": parsed_data["doc_type"],
                }
                for i in range(len(chunks))
            ],
        )

        logger.info(f"Stored {len(chunks)} chunks in DocumentStore")

        # Step 6: Analyze endpoints with AI
        self.update_state(
            state="PROCESSING",
            meta={
                "step": "analyzing",
                "progress": 80,
                "message": "Analyzing endpoints with AI...",
            },
        )

        analyzer = EndpointAnalyzer()
        analysis = analyzer.analyze_documentation(
            doc_text=parsed_data["raw_text"], base_url=base_url
        )

        logger.info(
            f"Found {len(analysis.get('endpoints', []))} endpoints via AI analysis"
        )

        # Step 7: Complete
        processing_time = time.time() - start_time

        result = {
            "document_id": document_id,
            "doc_type": parsed_data["doc_type"],
            "base_url": analysis.get("base_url") or base_url,
            "endpoints": analysis.get("endpoints", []),
            "summary": analysis.get("summary", ""),
            "chunks_count": len(chunks),
            "processing_time": processing_time,
            "status": "completed",
        }

        logger.info(
            f"✅ Document processing complete: {document_id} "
            f"({len(analysis.get('endpoints', []))} endpoints, {processing_time:.2f}s)"
        )

        return result

    except Exception as e:
        logger.exception(f"Error processing document {document_id}: {e}")

        # Update state to FAILURE with error details
        self.update_state(
            state="FAILURE",
            meta={
                "error": str(e),
                "error_type": type(e).__name__,
                "document_id": document_id,
            },
        )

        # Retry if not max retries
        raise self.retry(exc=e)


@celery_app.task(name="analyze_endpoints")
def analyze_endpoints_task(document_id: str, doc_text: str, base_url: str = None):
    """
    Analyze document and extract endpoints using AI

    Args:
        document_id: Document ID
        doc_text: Document text content
        base_url: Optional base URL

    Returns:
        dict: Endpoint analysis results
    """
    try:
        logger.info(f"🔍 Analyzing endpoints for document: {document_id}")

        analyzer = EndpointAnalyzer()
        analysis = analyzer.analyze_documentation(doc_text=doc_text, base_url=base_url)

        logger.info(
            f"✅ Analysis complete: {len(analysis.get('endpoints', []))} endpoints found"
        )

        return {
            "document_id": document_id,
            "endpoints": analysis.get("endpoints", []),
            "base_url": analysis.get("base_url"),
            "summary": analysis.get("summary"),
            "status": "completed",
        }

    except Exception as e:
        logger.exception(f"Error analyzing endpoints: {e}")
        raise


@celery_app.task(name="cleanup_document")
def cleanup_document_task(document_id: str):
    """
    Cleanup document resources

    Deletes ChromaDB collection and associated data

    Args:
        document_id: Document ID to cleanup

    Returns:
        dict: Cleanup status
    """
    try:
        logger.info(f"🧹 Cleaning up document: {document_id}")

        # Cleanup DocumentStore
        doc_store = DocumentStore(collection_name=f"doc_{document_id}")
        doc_store.cleanup()

        logger.info(f"✅ Document cleanup complete: {document_id}")

        return {"document_id": document_id, "status": "cleaned_up"}

    except Exception as e:
        logger.exception(f"Error cleaning up document: {e}")
        raise
