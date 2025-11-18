"""
Text Parser
AI-powered parser for plain text, PDF, and unstructured documentation
"""
import json
from typing import Dict, Any, Optional, Union

from loguru import logger

from src.ingestion.parsers.base import BaseParser, ParsingError
from src.ingestion.models import UnifiedAPISpec
from src.ai import get_ai_engine


class TextParser(BaseParser):
    """
    AI-powered text parser
    Uses hybrid AI engine (local/cloud) to extract API specification from text
    """

    def __init__(self):
        """Initialize text parser"""
        super().__init__()
        self.supported_formats = ['text', 'markdown', 'pdf', 'doc', 'docx']
        self.ai_engine = get_ai_engine()

    def can_parse(self, content: Union[str, Dict[str, Any]]) -> bool:
        """
        Text parser can handle any string content
        Should be used as fallback when other parsers fail
        """
        return isinstance(content, str) and len(content.strip()) > 0

    async def parse(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Parse text using AI

        Args:
            content: Text content (plain text, markdown, etc.)
            source_file: Optional source file path
            **kwargs: Additional arguments
                - task_complexity: AI task complexity ('simple', 'medium', 'complex')
                - use_custom_model: Whether to use custom fine-tuned model

        Returns:
            UnifiedAPISpec instance

        Raises:
            ParsingError: If parsing fails
        """
        try:
            if not isinstance(content, str):
                raise ParsingError("Text parser requires string content")

            content = content.strip()
            if not content:
                raise ParsingError("Empty content")

            logger.info(f"Parsing text content with AI ({len(content)} chars)")

            # Prepare prompt for AI
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(content)

            # Use AI to extract API specification
            task_complexity = kwargs.get('task_complexity', 'complex')
            use_custom_model = kwargs.get('use_custom_model', False)

            logger.info(f"Analyzing with AI (complexity: {task_complexity})")

            response = await self.ai_engine.analyze(
                prompt=user_prompt,
                system_prompt=system_prompt,
                task_complexity=task_complexity,
                use_custom_model=use_custom_model
            )

            # Parse AI response into UnifiedAPISpec
            spec = self._parse_ai_response(response, source_file)

            logger.info(
                f"AI extracted {len(spec.endpoints)} endpoints, "
                f"{len(spec.schemas)} schemas"
            )

            return spec

        except Exception as e:
            logger.error(f"Text parsing failed: {e}")
            raise ParsingError(f"Failed to parse text with AI: {e}")

    def _build_system_prompt(self) -> str:
        """Build system prompt for AI"""
        return """You are an expert API documentation analyzer. Your task is to extract complete API specification from any text format.

Extract the following information:
1. API title, version, and description
2. Base URL and servers
3. All endpoints (method, path, parameters, request/response)
4. Data schemas and models
5. Authentication/security schemes
6. Any validation constraints (min, max, pattern, etc.)

Output ONLY valid JSON in this exact format:
{
  "title": "API name",
  "version": "1.0.0",
  "description": "API description",
  "base_url": "https://api.example.com",
  "servers": [{"url": "https://api.example.com", "description": "Production"}],
  "endpoints": [
    {
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "/path/{param}",
      "summary": "Endpoint summary",
      "description": "Detailed description",
      "tags": ["tag1"],
      "parameters": [
        {
          "name": "param_name",
          "location": "path|query|header|body",
          "type": "string|integer|boolean|array|object",
          "required": true,
          "description": "Parameter description"
        }
      ],
      "request_body": {
        "content_type": "application/json",
        "required": true,
        "schema": {
          "type": "object",
          "properties": {},
          "required": []
        }
      },
      "responses": {
        "200": {
          "status_code": 200,
          "description": "Success response",
          "schema": {
            "type": "object",
            "properties": {}
          }
        }
      }
    }
  ],
  "schemas": {
    "ModelName": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  "security_schemes": {
    "api_key": {
      "type": "apiKey",
      "name": "X-API-Key",
      "location": "header"
    }
  }
}

Important:
- Output ONLY the JSON, no markdown, no explanations
- Be thorough - extract ALL endpoints and schemas
- Infer missing information from context
- Use proper HTTP methods and status codes
- Include all validation constraints you can find"""

    def _build_user_prompt(self, content: str) -> str:
        """Build user prompt with content"""
        # Truncate if too long (keep first and last parts)
        max_len = 15000
        if len(content) > max_len:
            half = max_len // 2
            content = f"{content[:half]}\n\n... (truncated) ...\n\n{content[-half:]}"

        return f"""Extract the complete API specification from this documentation:

{content}

Remember: Output ONLY valid JSON, no additional text."""

    def _parse_ai_response(
        self,
        response: str,
        source_file: Optional[str] = None
    ) -> UnifiedAPISpec:
        """Parse AI response into UnifiedAPISpec"""
        try:
            # Extract JSON from response (might have markdown code blocks)
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith('```'):
                lines = response.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response = '\n'.join(lines)

            # Parse JSON
            data = json.loads(response)

            # Add source information
            data['source_format'] = 'text'
            data['source_file'] = source_file

            # Create UnifiedAPISpec from parsed data
            # Pydantic will handle validation
            spec = UnifiedAPISpec(**data)

            return spec

        except json.JSONDecodeError as e:
            logger.error(f"AI response is not valid JSON: {e}")
            logger.debug(f"Response: {response[:500]}...")
            raise ParsingError(f"AI response is not valid JSON: {e}")

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise ParsingError(f"Failed to parse AI response: {e}")

    def parse_sync(
        self,
        content: Union[str, Dict[str, Any]],
        source_file: Optional[str] = None,
        **kwargs
    ) -> UnifiedAPISpec:
        """
        Synchronous parse method (calls async parse)

        Note: This is a workaround for BaseParser interface
        Use parse() with await for async contexts
        """
        import asyncio

        # Create event loop if not exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async parse
        return loop.run_until_complete(
            self.parse(content, source_file, **kwargs)
        )
