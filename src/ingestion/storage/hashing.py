"""
Document Hashing for Recognition
Content-based and semantic hashing for duplicate/similar document detection
"""
import hashlib
import json
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass

from loguru import logger

from src.ingestion.models import UnifiedAPISpec


def compute_content_hash(content: Union[str, Dict[str, Any]]) -> str:
    """
    Compute SHA-256 hash of content for exact duplicate detection

    Args:
        content: Raw content (string or dict)

    Returns:
        Hexadecimal hash string (64 chars)
    """
    # Normalize content to string
    if isinstance(content, dict):
        # Sort keys for consistent hashing
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
    else:
        content_str = str(content)

    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(content_str.encode('utf-8'))
    return hash_obj.hexdigest()


def compute_semantic_hash(spec: UnifiedAPISpec) -> str:
    """
    Compute semantic hash based on API structure (for similarity detection)

    This hash captures the "essence" of the API (endpoints, methods, paths)
    but ignores details like descriptions, examples, etc.

    Args:
        spec: Unified API specification

    Returns:
        Hexadecimal hash string representing API structure
    """
    # Extract structural features (only API structure, not metadata like title/version)
    structure = {
        'endpoints': sorted([
            {
                'method': endpoint.method,
                'path': _normalize_path(endpoint.path),
                'parameters': sorted([
                    {
                        'name': param.name,
                        'location': param.location,
                        'required': param.required
                    }
                    for param in endpoint.parameters
                ], key=lambda x: (x['location'], x['name']))
            }
            for endpoint in spec.endpoints
        ], key=lambda x: (x['method'], x['path'])),
        'schemas': sorted([
            {
                'name': name,
                'type': schema.type,
                'required': sorted(schema.required)
            }
            for name, schema in spec.schemas.items()
        ], key=lambda x: x['name'])
    }

    # Convert to JSON and hash
    structure_str = json.dumps(structure, sort_keys=True, separators=(',', ':'))
    hash_obj = hashlib.sha256(structure_str.encode('utf-8'))

    return hash_obj.hexdigest()


def _normalize_path(path: str) -> str:
    """
    Normalize API path for comparison

    Replaces path parameters with placeholders
    Examples:
        /users/{id} -> /users/{param}
        /users/:id -> /users/{param}
        /users/123 -> /users/{param} (if looks like ID)
    """
    import re

    # Replace {param} style
    path = re.sub(r'\{[^}]+\}', '{param}', path)

    # Replace :param style
    path = re.sub(r'/:([^/]+)', '/{param}', path)

    # Replace UUIDs (must be done before numeric IDs to avoid partial matches)
    path = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)',
        '/{param}',
        path,
        flags=re.IGNORECASE
    )

    # Replace numeric IDs
    path = re.sub(r'/\d+(?=/|$)', '/{param}', path)

    return path


def compute_endpoint_signatures(spec: UnifiedAPISpec) -> List[str]:
    """
    Compute unique signatures for each endpoint

    Args:
        spec: Unified API specification

    Returns:
        List of endpoint signature hashes
    """
    signatures = []

    for endpoint in spec.endpoints:
        # Create endpoint signature
        sig_data = {
            'method': endpoint.method,
            'path': _normalize_path(endpoint.path),
            'parameters': sorted([
                f"{param.location}:{param.name}"
                for param in endpoint.parameters
            ])
        }

        sig_str = json.dumps(sig_data, sort_keys=True)
        sig_hash = hashlib.md5(sig_str.encode('utf-8')).hexdigest()
        signatures.append(sig_hash)

    return signatures


@dataclass
class DocumentFingerprint:
    """
    Complete fingerprint of an API document
    Combines multiple hash types for comprehensive recognition
    """
    content_hash: str  # Exact content hash (SHA-256)
    semantic_hash: str  # Structural hash (SHA-256)
    endpoint_signatures: List[str]  # Individual endpoint signatures
    metadata: Dict[str, Any]  # Additional metadata

    @classmethod
    def from_content_and_spec(
        cls,
        content: Union[str, Dict[str, Any]],
        spec: UnifiedAPISpec,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> 'DocumentFingerprint':
        """
        Create fingerprint from raw content and parsed spec

        Args:
            content: Raw document content
            spec: Parsed unified API spec
            additional_metadata: Optional additional metadata

        Returns:
            DocumentFingerprint instance
        """
        content_hash = compute_content_hash(content)
        semantic_hash = compute_semantic_hash(spec)
        endpoint_sigs = compute_endpoint_signatures(spec)

        metadata = {
            'title': spec.title,
            'version': spec.version,
            'endpoint_count': len(spec.endpoints),
            'schema_count': len(spec.schemas),
            'source_format': spec.source_format,
            'source_file': spec.source_file
        }

        if additional_metadata:
            metadata.update(additional_metadata)

        return cls(
            content_hash=content_hash,
            semantic_hash=semantic_hash,
            endpoint_signatures=endpoint_sigs,
            metadata=metadata
        )

    @classmethod
    def from_spec_only(
        cls,
        spec: UnifiedAPISpec,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> 'DocumentFingerprint':
        """
        Create fingerprint from spec only (no raw content available)

        Args:
            spec: Parsed unified API spec
            additional_metadata: Optional additional metadata

        Returns:
            DocumentFingerprint instance
        """
        # Use spec JSON as content for hashing
        spec_dict = spec.model_dump(exclude_none=True, mode='json')
        content_hash = compute_content_hash(spec_dict)
        semantic_hash = compute_semantic_hash(spec)
        endpoint_sigs = compute_endpoint_signatures(spec)

        metadata = {
            'title': spec.title,
            'version': spec.version,
            'endpoint_count': len(spec.endpoints),
            'schema_count': len(spec.schemas),
            'source_format': spec.source_format,
            'source_file': spec.source_file
        }

        if additional_metadata:
            metadata.update(additional_metadata)

        return cls(
            content_hash=content_hash,
            semantic_hash=semantic_hash,
            endpoint_signatures=endpoint_sigs,
            metadata=metadata
        )

    def is_exact_match(self, other: 'DocumentFingerprint') -> bool:
        """Check if exact duplicate (same content hash)"""
        return self.content_hash == other.content_hash

    def is_semantic_match(self, other: 'DocumentFingerprint') -> bool:
        """Check if semantically identical (same structure)"""
        return self.semantic_hash == other.semantic_hash

    def compute_similarity(self, other: 'DocumentFingerprint') -> float:
        """
        Compute similarity score with another fingerprint

        Uses Jaccard similarity on endpoint signatures

        Args:
            other: Another fingerprint to compare

        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)
        """
        if not self.endpoint_signatures or not other.endpoint_signatures:
            return 0.0

        # Jaccard similarity: intersection / union
        set_a = set(self.endpoint_signatures)
        set_b = set(other.endpoint_signatures)

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        if union == 0:
            return 0.0

        return intersection / union

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'content_hash': self.content_hash,
            'semantic_hash': self.semantic_hash,
            'endpoint_signatures': self.endpoint_signatures,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentFingerprint':
        """Create from dictionary"""
        return cls(
            content_hash=data['content_hash'],
            semantic_hash=data['semantic_hash'],
            endpoint_signatures=data['endpoint_signatures'],
            metadata=data.get('metadata', {})
        )

    def __repr__(self) -> str:
        return (
            f"DocumentFingerprint("
            f"content={self.content_hash[:8]}..., "
            f"semantic={self.semantic_hash[:8]}..., "
            f"endpoints={len(self.endpoint_signatures)})"
        )
