"""
Text Splitter Module
Semantic chunking for RAG with configurable chunk size and overlap
"""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from src.config import settings


class DocumentChunker:
    """
    Split documents into chunks for RAG retrieval
    Uses RecursiveCharacterTextSplitter for semantic splitting
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        Initialize chunker

        Args:
            chunk_size: Size of each chunk (default from settings)
            chunk_overlap: Overlap between chunks (default from settings)
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n\n",  # Multiple newlines (section breaks)
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ". ",      # Sentence breaks
                ", ",      # Phrase breaks
                " ",       # Word breaks
                "",        # Character breaks (last resort)
            ],
        )

        logger.info(
            f"Initialized DocumentChunker: "
            f"chunk_size={self.chunk_size}, overlap={self.chunk_overlap}"
        )

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if not text:
            logger.warning("Empty text provided to chunker")
            return []

        chunks = self.splitter.split_text(text)

        logger.info(
            f"Split text into {len(chunks)} chunks "
            f"(total chars: {len(text)}, "
            f"avg chunk size: {len(text) // len(chunks) if chunks else 0})"
        )

        return chunks

    def chunk_documents(self, texts: List[str]) -> List[str]:
        """
        Split multiple documents into chunks

        Args:
            texts: List of document texts

        Returns:
            Flattened list of all chunks
        """
        all_chunks = []

        for idx, text in enumerate(texts):
            logger.debug(f"Chunking document {idx + 1}/{len(texts)}")
            chunks = self.chunk_text(text)
            all_chunks.extend(chunks)

        logger.info(
            f"Chunked {len(texts)} documents into {len(all_chunks)} total chunks"
        )

        return all_chunks

    def chunk_with_metadata(
        self, text: str, metadata: dict = None
    ) -> List[dict]:
        """
        Split text into chunks with metadata attached

        Args:
            text: Text to split
            metadata: Metadata to attach to each chunk

        Returns:
            List of dicts with 'text' and 'metadata' keys
        """
        chunks = self.chunk_text(text)
        metadata = metadata or {}

        chunks_with_metadata = []
        for idx, chunk in enumerate(chunks):
            chunk_data = {
                "text": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk),
                }
            }
            chunks_with_metadata.append(chunk_data)

        return chunks_with_metadata

    def get_chunk_stats(self, chunks: List[str]) -> dict:
        """
        Get statistics about chunks

        Args:
            chunks: List of text chunks

        Returns:
            Dict with statistics
        """
        if not chunks:
            return {
                "num_chunks": 0,
                "total_chars": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
            }

        chunk_sizes = [len(chunk) for chunk in chunks]

        return {
            "num_chunks": len(chunks),
            "total_chars": sum(chunk_sizes),
            "avg_chunk_size": sum(chunk_sizes) // len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
        }
