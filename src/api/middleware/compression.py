"""
Response Compression Middleware
Compresses responses using gzip to reduce bandwidth and improve performance
"""
import gzip
from typing import Callable
from io import BytesIO

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger

from src.config import settings


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for compressing HTTP responses

    Features:
    - Automatic gzip compression for responses > 1KB
    - Respects Accept-Encoding header
    - Skips already compressed content
    - Configurable compression level
    - Performance metrics logging
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,  # 1KB minimum
        compression_level: int = 6,  # 1-9, 6 is balanced
        excluded_paths: list = None
    ):
        """
        Initialize compression middleware

        Args:
            app: ASGI application
            minimum_size: Minimum response size in bytes to compress
            compression_level: Gzip compression level (1-9, higher = better compression but slower)
            excluded_paths: List of paths to skip compression (e.g., ['/health', '/metrics'])
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.excluded_paths = excluded_paths or ['/health', '/metrics']

        # Content types that benefit from compression
        self.compressible_types = {
            'application/json',
            'application/xml',
            'text/html',
            'text/plain',
            'text/css',
            'text/javascript',
            'application/javascript',
            'image/svg+xml'
        }

        # Content types to never compress (already compressed)
        self.excluded_types = {
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'video/',
            'audio/',
            'application/zip',
            'application/gzip',
            'application/pdf'
        }

    def should_compress(
        self,
        request: Request,
        response: Response,
        body: bytes
    ) -> bool:
        """
        Determine if response should be compressed

        Args:
            request: Incoming request
            response: Outgoing response
            body: Response body bytes

        Returns:
            True if should compress, False otherwise
        """
        # Skip if path is excluded
        if request.url.path in self.excluded_paths:
            return False

        # Skip if body too small
        if len(body) < self.minimum_size:
            return False

        # Check if client accepts gzip
        accept_encoding = request.headers.get('accept-encoding', '').lower()
        if 'gzip' not in accept_encoding:
            return False

        # Check content type
        content_type = response.headers.get('content-type', '').lower()

        # Don't compress already compressed content
        for excluded_type in self.excluded_types:
            if content_type.startswith(excluded_type):
                return False

        # Check if content type is compressible
        for compressible_type in self.compressible_types:
            if content_type.startswith(compressible_type):
                return True

        # Default: don't compress unknown types
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and compress response if appropriate

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response (compressed if appropriate)
        """
        # Get response from next handler
        response = await call_next(request)

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Check if we should compress
        if not self.should_compress(request, response, body):
            # Return original response
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        # Compress the body
        try:
            compressed_body = gzip.compress(
                body,
                compresslevel=self.compression_level
            )

            original_size = len(body)
            compressed_size = len(compressed_body)
            compression_ratio = (1 - compressed_size / original_size) * 100

            # Log compression stats (at debug level to avoid spam)
            logger.debug(
                f"Compressed response: {original_size} -> {compressed_size} bytes "
                f"({compression_ratio:.1f}% reduction)",
                path=request.url.path,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio
            )

            # Update headers
            headers = dict(response.headers)
            headers['content-encoding'] = 'gzip'
            headers['content-length'] = str(compressed_size)
            headers['vary'] = 'Accept-Encoding'

            # Remove Content-Length if present (we're changing the body)
            headers.pop('content-length', None)

            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")
            # Return uncompressed on error
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )


def add_compression_middleware(app, **kwargs):
    """
    Helper function to add compression middleware to FastAPI app

    Usage:
        add_compression_middleware(app, minimum_size=500, compression_level=9)

    Args:
        app: FastAPI application
        **kwargs: Arguments to pass to CompressionMiddleware
    """
    app.add_middleware(CompressionMiddleware, **kwargs)
    logger.info(
        f"✅ Compression middleware enabled "
        f"(min_size={kwargs.get('minimum_size', 1024)}B, "
        f"level={kwargs.get('compression_level', 6)})"
    )
