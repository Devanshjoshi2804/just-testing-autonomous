"""
Data Flow Tracker
Tracks data flow between API requests
Extracts IDs/values from responses and injects into subsequent requests
"""
import re
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

# Optional logger
try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


@dataclass
class ExtractedValue:
    """Represents a value extracted from an API response"""
    value: Any
    source_endpoint: str
    field_name: str
    extraction_pattern: str
    confidence: float  # 0.0 to 1.0


class DataFlowTracker:
    """
    Tracks data flow between API requests

    Responsibilities:
    1. Extract IDs and important values from API responses
    2. Store extracted values in session context
    3. Inject extracted values into subsequent requests
    4. Handle path parameter substitution (/users/{id} → /users/123)
    5. Handle request body field injection

    Example flow:
    1. POST /users → response: {"id": "user_123", "email": "..."}
    2. Extract: user_id = "user_123"
    3. GET /users/{id} → substitute: GET /users/user_123
    4. POST /orders with body {user_id: ???} → inject: {user_id: "user_123"}
    """

    def __init__(self):
        # Storage for extracted values
        # Format: {field_name: ExtractedValue}
        self.extracted_values: Dict[str, ExtractedValue] = {}

        # Patterns for ID extraction
        self.id_patterns = [
            r'"id":\s*"?([^",\s}]+)"?',           # "id": "123" or "id": 123
            r'"([a-z_]+_id)":\s*"?([^",\s}]+)"?',  # "user_id": "123"
            r'"([a-z]+Id)":\s*"?([^",\s}]+)"?',    # "userId": "123" (camelCase)
            r'"uuid":\s*"([^"]+)"',                # "uuid": "550e8400-..."
            r'"([a-z_]+_uuid)":\s*"([^"]+)"',      # "user_uuid": "550e8400-..."
        ]

    def extract_from_response(
        self,
        endpoint_key: str,
        response_body: Dict[str, Any],
        status_code: int
    ) -> List[ExtractedValue]:
        """
        Extract important values from API response

        Args:
            endpoint_key: Endpoint that generated this response (e.g., "POST /users")
            response_body: Response body as dict
            status_code: HTTP status code

        Returns:
            List of extracted values
        """
        extracted = []

        # Only extract from successful responses
        if not (200 <= status_code < 300):
            return extracted

        # Convert response to JSON string for pattern matching
        response_json = json.dumps(response_body)

        # Extract using patterns
        for pattern in self.id_patterns:
            matches = re.finditer(pattern, response_json)
            for match in matches:
                if len(match.groups()) == 1:
                    # Simple pattern like "id": "123"
                    field_name = 'id'
                    value = match.group(1)
                elif len(match.groups()) == 2:
                    # Pattern with field name like "user_id": "123"
                    field_name = match.group(1)
                    value = match.group(2)
                else:
                    continue

                # Create extracted value
                extracted_value = ExtractedValue(
                    value=value,
                    source_endpoint=endpoint_key,
                    field_name=field_name,
                    extraction_pattern=pattern,
                    confidence=0.9
                )

                extracted.append(extracted_value)

                # Store in extracted values (latest value wins)
                self.extracted_values[field_name] = extracted_value

                logger.debug(
                    f"  📥 Extracted {field_name}={value} from {endpoint_key}"
                )

        # Also try direct dict access for common ID fields
        id_field_names = ['id', 'uuid', 'user_id', 'userId', 'order_id', 'orderId']
        for field_name in id_field_names:
            if field_name in response_body:
                value = response_body[field_name]

                extracted_value = ExtractedValue(
                    value=value,
                    source_endpoint=endpoint_key,
                    field_name=field_name,
                    extraction_pattern='direct_access',
                    confidence=1.0  # Direct access is most confident
                )

                extracted.append(extracted_value)
                self.extracted_values[field_name] = extracted_value

                logger.debug(
                    f"  📥 Extracted {field_name}={value} from {endpoint_key}"
                )

        return extracted

    def inject_into_path(
        self,
        path: str,
        resource_hint: Optional[str] = None
    ) -> str:
        """
        Inject extracted values into path parameters

        Args:
            path: Path template (e.g., "/users/{id}")
            resource_hint: Resource name hint (e.g., "users")

        Returns:
            Path with substituted values (e.g., "/users/123")
        """
        # Find all path parameters
        param_pattern = r'\{([^}]+)\}'
        params = re.findall(param_pattern, path)

        if not params:
            return path

        result_path = path

        for param in params:
            # Try to find matching extracted value
            value = self._find_matching_value(param, resource_hint)

            if value is not None:
                # Substitute {param} with value
                result_path = result_path.replace(f'{{{param}}}', str(value))
                logger.debug(f"  💉 Injected {param}={value} into path")
            else:
                logger.warning(
                    f"  ⚠️  Could not find value for path parameter: {param}"
                )

        return result_path

    def inject_into_body(
        self,
        body: Dict[str, Any],
        resource_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inject extracted values into request body

        Args:
            body: Request body dict
            resource_hint: Resource name hint

        Returns:
            Body with injected values
        """
        result_body = body.copy()

        for field_name, current_value in body.items():
            # Check if field looks like an ID field
            if self._is_id_field(field_name):
                # Try to find matching extracted value
                value = self._find_matching_value(field_name, resource_hint)

                if value is not None:
                    result_body[field_name] = value
                    logger.debug(f"  💉 Injected {field_name}={value} into body")

        return result_body

    def _is_id_field(self, field_name: str) -> bool:
        """Check if field name looks like an ID field"""
        id_indicators = ['id', 'uuid', 'key']
        field_lower = field_name.lower()
        return any(indicator in field_lower for indicator in id_indicators)

    def _find_matching_value(
        self,
        field_name: str,
        resource_hint: Optional[str] = None
    ) -> Optional[Any]:
        """
        Find matching extracted value for a field

        Args:
            field_name: Field to find value for (e.g., "id", "user_id")
            resource_hint: Resource name (e.g., "users")

        Returns:
            Extracted value or None
        """
        # Try exact match first
        if field_name in self.extracted_values:
            return self.extracted_values[field_name].value

        # Try normalized match (handle camelCase vs snake_case)
        normalized_field = self._normalize_field_name(field_name)
        for extracted_field, extracted_value in self.extracted_values.items():
            if self._normalize_field_name(extracted_field) == normalized_field:
                return extracted_value.value

        # If field is just "id" and we have resource hint, try {resource}_id
        if field_name == 'id' and resource_hint:
            resource_id_field = f'{resource_hint}_id'
            if resource_id_field in self.extracted_values:
                return self.extracted_values[resource_id_field].value

        # Try resource-based matching
        if resource_hint:
            # Try {resource}_id
            resource_id = f'{resource_hint}_id'
            if resource_id in self.extracted_values:
                return self.extracted_values[resource_id].value

            # Try {resource}Id (camelCase)
            resource_id_camel = f'{resource_hint}Id'
            if resource_id_camel in self.extracted_values:
                return self.extracted_values[resource_id_camel].value

        # Fallback: return most recent "id" if available
        if 'id' in self.extracted_values:
            return self.extracted_values['id'].value

        return None

    def _normalize_field_name(self, field_name: str) -> str:
        """
        Normalize field name for comparison

        Examples:
        - user_id → userid
        - userId → userid
        - UserID → userid
        """
        # Remove underscores and convert to lowercase
        return re.sub(r'[_\s-]', '', field_name.lower())

    def get_extracted_summary(self) -> Dict[str, Any]:
        """
        Get summary of extracted values

        Returns:
            Summary dict with counts and fields
        """
        return {
            'total_extracted': len(self.extracted_values),
            'fields': list(self.extracted_values.keys()),
            'values': {
                field: {
                    'value': str(ev.value)[:50],  # Truncate for display
                    'source': ev.source_endpoint,
                    'confidence': ev.confidence
                }
                for field, ev in self.extracted_values.items()
            }
        }

    def clear(self) -> None:
        """Clear all extracted values (for new test session)"""
        self.extracted_values.clear()
        logger.debug("🧹 Cleared extracted values")

    def has_value_for_field(self, field_name: str) -> bool:
        """Check if we have extracted value for a field"""
        return field_name in self.extracted_values

    def get_value(self, field_name: str) -> Optional[Any]:
        """Get extracted value for a field"""
        if field_name in self.extracted_values:
            return self.extracted_values[field_name].value
        return None

    def inject_into_endpoint(
        self,
        endpoint: Dict[str, Any],
        resource_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inject extracted values into entire endpoint (path + body)

        Args:
            endpoint: Endpoint dict with 'path' and optional 'payload'
            resource_hint: Resource name hint

        Returns:
            Modified endpoint with injected values
        """
        result_endpoint = endpoint.copy()

        # Inject into path
        if 'path' in result_endpoint:
            result_endpoint['path'] = self.inject_into_path(
                result_endpoint['path'],
                resource_hint
            )

        # Inject into payload/body
        if 'payload' in result_endpoint and isinstance(result_endpoint['payload'], dict):
            result_endpoint['payload'] = self.inject_into_body(
                result_endpoint['payload'],
                resource_hint
            )

        return result_endpoint
