"""
Flow Store - ChromaDB for Test Execution State
Stores API requests/responses during test execution for intelligent retry and context
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from mistralai import Mistral
from loguru import logger

from src.config import settings


class FlowStore:
    """
    ChromaDB store for test execution flow data
    Stores requests/responses with semantic search for intelligent retry
    """

    def __init__(
        self,
        session_id: str,
        persist_directory: str = None,
    ):
        """
        Initialize Flow Store for a test session

        Args:
            session_id: Unique ID for this test session
            persist_directory: Directory for persistent storage
        """
        self.session_id = session_id
        self.collection_name = f"test_flow_{session_id}"
        self.persist_directory = persist_directory or "./data/flow_chroma_db"

        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize Mistral for embeddings
        self.mistral_client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL

        # Create collection for this session
        try:
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Created Flow Store for session: {session_id}")
        except:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing Flow Store: {session_id}")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = self.mistral_client.embeddings.create(
                model=self.embedding_model,
                inputs=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def store_request(
        self,
        endpoint_key: str,
        request_payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store API request in flow database

        Args:
            endpoint_key: Unique key for endpoint (e.g., "POST /api/login")
            request_payload: Request payload dict
            metadata: Optional additional metadata
        """
        doc_text = (
            f"REQUEST for {endpoint_key}:\n"
            f"{json.dumps(request_payload, indent=2)}"
        )

        # Generate embedding
        embedding = self._generate_embedding(doc_text)

        # Prepare metadata
        meta = {
            "type": "request",
            "endpoint": endpoint_key,
            "session_id": self.session_id,
            **(metadata or {})
        }

        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[f"{endpoint_key}_request"]
        )

        logger.debug(f"💾 Stored request: {endpoint_key}")

    def store_response(
        self,
        endpoint_key: str,
        response_data: Dict[str, Any],
        status_code: int,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store API response in flow database

        Args:
            endpoint_key: Unique key for endpoint
            response_data: Response data dict
            status_code: HTTP status code
            success: Whether request was successful
            metadata: Optional additional metadata
        """
        doc_text = (
            f"RESPONSE from {endpoint_key} (Status: {status_code}):\n"
            f"{json.dumps(response_data, indent=2)}"
        )

        # Generate embedding
        embedding = self._generate_embedding(doc_text)

        # Prepare metadata
        meta = {
            "type": "response",
            "endpoint": endpoint_key,
            "status_code": str(status_code),
            "success": str(success),
            "session_id": self.session_id,
            **(metadata or {})
        }

        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[f"{endpoint_key}_response"]
        )

        logger.debug(f"💾 Stored response: {endpoint_key} ({status_code})")

    def query_for_context(
        self,
        query: str,
        n_results: int = 3,
        filter_type: Optional[str] = None
    ) -> str:
        """
        Query flow database for relevant context

        Args:
            query: Query string (e.g., "Find authentication token")
            n_results: Number of results to return
            filter_type: Optional filter for "request" or "response"

        Returns:
            Combined text from relevant documents
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build where clause if filtering by type
        where = {"type": filter_type} if filter_type else None

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        if not results["documents"] or not results["documents"][0]:
            logger.debug(f"No context found for query: {query[:50]}...")
            return "No previous flow data found."

        # Combine relevant documents
        combined_text = "\n\n---\n\n".join(results["documents"][0])

        logger.debug(
            f"Found {len(results['documents'][0])} context items for: {query[:50]}..."
        )

        return combined_text

    def get_successful_responses(self) -> List[Dict[str, Any]]:
        """
        Get all successful API responses from this session

        Returns:
            List of response documents with metadata
        """
        results = self.collection.get(
            where={"type": "response", "success": "True"}
        )

        responses = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            responses.append({
                "document": doc,
                "metadata": meta
            })

        logger.info(f"Retrieved {len(responses)} successful responses")
        return responses

    def get_all_endpoints_tested(self) -> List[str]:
        """
        Get list of all endpoints tested in this session

        Returns:
            List of endpoint keys
        """
        results = self.collection.get()

        endpoints = set()
        for meta in results["metadatas"]:
            if "endpoint" in meta:
                endpoints.add(meta["endpoint"])

        return sorted(list(endpoints))

    def cleanup(self) -> None:
        """Delete this session's collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"🗑️ Cleaned up Flow Store: {self.session_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup Flow Store: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get flow store statistics

        Returns:
            Dict with stats
        """
        all_data = self.collection.get()
        total_count = len(all_data["documents"])

        request_count = sum(
            1 for meta in all_data["metadatas"]
            if meta.get("type") == "request"
        )

        response_count = sum(
            1 for meta in all_data["metadatas"]
            if meta.get("type") == "response"
        )

        success_count = sum(
            1 for meta in all_data["metadatas"]
            if meta.get("success") == "True"
        )

        return {
            "session_id": self.session_id,
            "total_items": total_count,
            "requests": request_count,
            "responses": response_count,
            "successful_responses": success_count,
            "endpoints_tested": len(self.get_all_endpoints_tested()),
        }
