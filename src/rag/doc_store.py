"""
Document Store - ChromaDB for API Documentation
Stores parsed documentation chunks with embeddings for semantic search
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from mistralai import Mistral
from loguru import logger

from src.config import settings


class DocumentStore:
    """
    ChromaDB store for API documentation
    Handles embedding generation and semantic search for document chunks
    """

    def __init__(
        self,
        collection_name: str = "api_documentation",
        persist_directory: str = None,
    ):
        """
        Initialize Document Store

        Args:
            collection_name: Name of ChromaDB collection
            persist_directory: Directory for persistent storage
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./data/doc_chroma_db"

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

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Created new collection: {self.collection_name}")

        logger.info(f"Document Store initialized at: {self.persist_directory}")

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using sentence-transformers (local)

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            # Use sentence-transformers for local embeddings
            from sentence_transformers import SentenceTransformer
            
            # Load model (cached after first use)
            if not hasattr(self, '_embedding_model_loaded'):
                self._local_model = SentenceTransformer('all-MiniLM-L6-v2')
                self._embedding_model_loaded = True
            
            embeddings = self._local_model.encode(texts, convert_to_numpy=True).tolist()
            logger.debug(f"Generated {len(embeddings)} embeddings using local model")

            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        Add documents to the store with embeddings

        Args:
            texts: List of document texts/chunks
            metadatas: Optional list of metadata dicts
            ids: Optional list of document IDs
        """
        if not texts:
            logger.warning("No texts provided to add_documents")
            return

        # Generate IDs if not provided
        if ids is None:
            existing_count = self.collection.count()
            ids = [f"doc_{existing_count + i}" for i in range(len(texts))]

        # Generate metadata if not provided
        if metadatas is None:
            metadatas = [{"chunk_index": i} for i in range(len(texts))]

        # Ensure all metadata values are JSON-serializable strings/numbers
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for key, value in meta.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_meta[key] = value
                else:
                    clean_meta[key] = str(value)
            clean_metadatas.append(clean_meta)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} documents...")
        embeddings = self._generate_embeddings(texts)

        # Add to ChromaDB
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=clean_metadatas,
            ids=ids
        )

        logger.info(f"✅ Added {len(texts)} documents to {self.collection_name}")

    def query(
        self,
        query_text: str,
        n_results: int = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Semantic search for relevant documents

        Args:
            query_text: Query string
            n_results: Number of results to return (default from settings)
            where: Optional metadata filter

        Returns:
            Dict with documents, metadatas, distances, ids
        """
        n_results = n_results or settings.RAG_TOP_K

        # Generate query embedding
        query_embedding = self._generate_embeddings([query_text])[0]

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        logger.info(
            f"Query: '{query_text[:50]}...' → Found {len(results['documents'][0])} results"
        )

        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else [],
        }

    def get_all_documents(self) -> Dict[str, Any]:
        """
        Get all documents from the collection

        Returns:
            Dict with all documents and metadata
        """
        results = self.collection.get()

        return {
            "documents": results["documents"],
            "metadatas": results["metadatas"],
            "ids": results["ids"],
            "count": len(results["documents"]),
        }

    def delete_collection(self) -> None:
        """Delete the entire collection"""
        self.client.delete_collection(name=self.collection_name)
        logger.warning(f"🗑️ Deleted collection: {self.collection_name}")

    def clear_collection(self) -> None:
        """Clear all documents from collection but keep the collection"""
        # Delete and recreate
        try:
            self.client.delete_collection(name=self.collection_name)
        except:
            pass

        self.collection = self.client.create_collection(name=self.collection_name)
        logger.warning(f"🗑️ Cleared collection: {self.collection_name}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Dict with collection stats
        """
        count = self.collection.count()

        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": self.persist_directory,
            "embedding_model": self.embedding_model,
        }
