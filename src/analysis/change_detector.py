"""
API Change Detection
Detects changes in API behavior for self-healing tests
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import json

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
class APIChange:
    """Represents a detected change in API behavior"""
    change_type: str  # 'status_code', 'schema', 'field_added', 'field_removed', 'type_changed', 'value_changed'
    severity: str  # 'BREAKING', 'NON_BREAKING', 'MINOR'
    field_path: str  # JSONPath to changed field
    expected_value: Any
    actual_value: Any
    description: str
    suggestion: str  # How to fix the test
    detected_at: datetime


class ChangeDetector:
    """
    Detects changes in API responses compared to test expectations

    Identifies:
    - Status code changes
    - Schema changes (new/removed/renamed fields)
    - Type changes (string → int, etc.)
    - Value changes (different data)
    - Response structure changes
    """

    def __init__(self):
        logger.info("ChangeDetector initialized")

    def detect_changes(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        test_metadata: Optional[Dict[str, Any]] = None
    ) -> List[APIChange]:
        """
        Detect changes between expected and actual API responses

        Args:
            expected: Expected response from test
            actual: Actual response from API
            test_metadata: Optional test metadata for context

        Returns:
            List of detected changes
        """
        changes = []

        expected_status = expected.get('status_code', 200)
        actual_status = actual.get('status_code', 0)
        expected_body = expected.get('body', {})
        actual_body = actual.get('body', {})

        # 1. Detect status code changes
        if expected_status != actual_status:
            change = self._detect_status_code_change(
                expected_status,
                actual_status,
                test_metadata
            )
            changes.append(change)

        # 2. Detect schema changes in response body
        if isinstance(expected_body, dict) and isinstance(actual_body, dict):
            schema_changes = self._detect_schema_changes(
                expected_body,
                actual_body,
                path=""
            )
            changes.extend(schema_changes)

        # 3. Detect response type changes
        elif type(expected_body) != type(actual_body):
            changes.append(APIChange(
                change_type='response_type_changed',
                severity='BREAKING',
                field_path='response.body',
                expected_value=type(expected_body).__name__,
                actual_value=type(actual_body).__name__,
                description=f"Response type changed from {type(expected_body).__name__} to {type(actual_body).__name__}",
                suggestion="Update test to expect new response type",
                detected_at=datetime.now()
            ))

        logger.info(f"Detected {len(changes)} API changes")
        return changes

    def _detect_status_code_change(
        self,
        expected: int,
        actual: int,
        test_metadata: Optional[Dict] = None
    ) -> APIChange:
        """Detect and classify status code changes"""

        # Determine severity
        severity = 'BREAKING'

        # Success → Error (BREAKING)
        if 200 <= expected < 300 and actual >= 400:
            severity = 'BREAKING'
            description = f"API now returns error {actual} instead of success {expected}"
            suggestion = "Check if API requirements changed or endpoint was modified"

        # Error → Success (API fixed!)
        elif expected >= 400 and 200 <= actual < 300:
            severity = 'NON_BREAKING'
            description = f"API now succeeds with {actual} instead of failing with {expected}"
            suggestion = "Update test to expect success - API may have been fixed"

        # Different success codes (minor)
        elif 200 <= expected < 300 and 200 <= actual < 300:
            severity = 'MINOR'
            description = f"Success code changed from {expected} to {actual}"
            suggestion = "Update expected status code"

        # Different error codes
        elif expected >= 400 and actual >= 400:
            severity = 'MINOR'
            description = f"Error code changed from {expected} to {actual}"
            suggestion = "Update expected error code"

        else:
            description = f"Status code changed from {expected} to {actual}"
            suggestion = "Update expected status code"

        return APIChange(
            change_type='status_code',
            severity=severity,
            field_path='response.status_code',
            expected_value=expected,
            actual_value=actual,
            description=description,
            suggestion=suggestion,
            detected_at=datetime.now()
        )

    def _detect_schema_changes(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        path: str = ""
    ) -> List[APIChange]:
        """
        Recursively detect schema changes in nested dicts

        Args:
            expected: Expected schema
            actual: Actual schema
            path: Current path in schema (JSONPath)

        Returns:
            List of schema changes
        """
        changes = []

        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())

        # 1. Detect added fields (NON_BREAKING)
        added_keys = actual_keys - expected_keys
        for key in added_keys:
            field_path = f"{path}.{key}" if path else key
            changes.append(APIChange(
                change_type='field_added',
                severity='NON_BREAKING',
                field_path=field_path,
                expected_value=None,
                actual_value=actual[key],
                description=f"New field '{field_path}' added to response",
                suggestion=f"Optionally add '{field_path}' to test expectations",
                detected_at=datetime.now()
            ))

        # 2. Detect removed fields (BREAKING)
        removed_keys = expected_keys - actual_keys
        for key in removed_keys:
            field_path = f"{path}.{key}" if path else key
            changes.append(APIChange(
                change_type='field_removed',
                severity='BREAKING',
                field_path=field_path,
                expected_value=expected[key],
                actual_value=None,
                description=f"Field '{field_path}' removed from response",
                suggestion=f"Remove '{field_path}' from test expectations or check if field was renamed",
                detected_at=datetime.now()
            ))

        # 3. Detect changes in existing fields
        common_keys = expected_keys & actual_keys
        for key in common_keys:
            field_path = f"{path}.{key}" if path else key
            expected_value = expected[key]
            actual_value = actual[key]

            # Type changed (BREAKING)
            if type(expected_value) != type(actual_value):
                # Exception: None → value (API now returns data)
                if expected_value is None and actual_value is not None:
                    changes.append(APIChange(
                        change_type='field_now_populated',
                        severity='NON_BREAKING',
                        field_path=field_path,
                        expected_value=None,
                        actual_value=actual_value,
                        description=f"Field '{field_path}' now returns {type(actual_value).__name__} instead of null",
                        suggestion=f"Update test to expect {type(actual_value).__name__}",
                        detected_at=datetime.now()
                    ))
                else:
                    changes.append(APIChange(
                        change_type='type_changed',
                        severity='BREAKING',
                        field_path=field_path,
                        expected_value=f"{type(expected_value).__name__}: {expected_value}",
                        actual_value=f"{type(actual_value).__name__}: {actual_value}",
                        description=f"Field '{field_path}' type changed from {type(expected_value).__name__} to {type(actual_value).__name__}",
                        suggestion=f"Update test to expect {type(actual_value).__name__}",
                        detected_at=datetime.now()
                    ))

            # Nested dict - recurse
            elif isinstance(expected_value, dict) and isinstance(actual_value, dict):
                nested_changes = self._detect_schema_changes(
                    expected_value,
                    actual_value,
                    field_path
                )
                changes.extend(nested_changes)

            # List - check structure
            elif isinstance(expected_value, list) and isinstance(actual_value, list):
                list_changes = self._detect_list_changes(
                    expected_value,
                    actual_value,
                    field_path
                )
                changes.extend(list_changes)

            # Value changed (MINOR - could be test data)
            elif expected_value != actual_value:
                # Only flag if values are structurally different, not just data
                if self._is_structural_change(expected_value, actual_value):
                    changes.append(APIChange(
                        change_type='value_changed',
                        severity='MINOR',
                        field_path=field_path,
                        expected_value=expected_value,
                        actual_value=actual_value,
                        description=f"Field '{field_path}' value changed from '{expected_value}' to '{actual_value}'",
                        suggestion="Check if this is expected data variation or schema change",
                        detected_at=datetime.now()
                    ))

        return changes

    def _detect_list_changes(
        self,
        expected: List,
        actual: List,
        path: str
    ) -> List[APIChange]:
        """Detect changes in list fields"""
        changes = []

        # List length changed
        if len(expected) != len(actual):
            changes.append(APIChange(
                change_type='list_length_changed',
                severity='MINOR',
                field_path=path,
                expected_value=f"length {len(expected)}",
                actual_value=f"length {len(actual)}",
                description=f"List '{path}' length changed from {len(expected)} to {len(actual)}",
                suggestion="Check if this is expected or update test",
                detected_at=datetime.now()
            ))

        # Check item structure (if both have items)
        if expected and actual:
            # Compare first items to check structure
            if isinstance(expected[0], dict) and isinstance(actual[0], dict):
                item_changes = self._detect_schema_changes(
                    expected[0],
                    actual[0],
                    f"{path}[0]"
                )
                # Only report structural changes, not value changes
                structural_changes = [
                    c for c in item_changes
                    if c.change_type != 'value_changed'
                ]
                changes.extend(structural_changes)

        return changes

    def _is_structural_change(self, expected: Any, actual: Any) -> bool:
        """
        Determine if a value change is structural or just data variation

        Structural: "email" → "username" (field purpose changed)
        Data: "john@example.com" → "jane@example.com" (just different data)
        """
        # If both are strings, check if they look like the same type of data
        if isinstance(expected, str) and isinstance(actual, str):
            # Email addresses
            if '@' in expected and '@' in actual:
                return False  # Just different email

            # URLs
            if expected.startswith('http') and actual.startswith('http'):
                return False  # Just different URL

            # UUIDs/IDs (long hex strings)
            if len(expected) > 20 and len(actual) > 20:
                return False  # Just different ID

            # If values are very different in nature, it's structural
            if len(expected) > 0 and len(actual) > 0:
                if expected.isdigit() != actual.isdigit():
                    return True  # Changed from numeric to text or vice versa

        # Numbers - small changes are data, large changes might be structural
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            # If both are small integers, likely just different data
            if abs(expected) < 1000 and abs(actual) < 1000:
                return False

        # Default: flag as potentially structural
        return True

    def categorize_changes(self, changes: List[APIChange]) -> Dict[str, List[APIChange]]:
        """Categorize changes by severity"""
        categorized = {
            'BREAKING': [],
            'NON_BREAKING': [],
            'MINOR': []
        }

        for change in changes:
            categorized[change.severity].append(change)

        return categorized

    def should_auto_heal(self, changes: List[APIChange]) -> bool:
        """
        Determine if changes are safe to auto-heal

        Auto-heal criteria:
        - No BREAKING changes, OR
        - Only non-destructive BREAKING changes (new success status, fields added)
        """
        categorized = self.categorize_changes(changes)
        breaking = categorized['BREAKING']

        # No breaking changes - safe to auto-heal
        if not breaking:
            return True

        # Check if breaking changes are actually improvements
        safe_breaking_types = {
            'field_now_populated',  # Null → value
        }

        # All breaking changes are safe types
        if all(c.change_type in safe_breaking_types for c in breaking):
            return True

        # Has destructive breaking changes - require manual review
        return False

    def generate_change_report(self, changes: List[APIChange]) -> str:
        """Generate human-readable change report"""
        if not changes:
            return "No API changes detected"

        categorized = self.categorize_changes(changes)

        report = []
        report.append(f"\n🔄 API CHANGE DETECTION REPORT")
        report.append(f"{'=' * 60}\n")
        report.append(f"Total changes detected: {len(changes)}\n")

        for severity in ['BREAKING', 'NON_BREAKING', 'MINOR']:
            severity_changes = categorized[severity]
            if severity_changes:
                icon = '🔴' if severity == 'BREAKING' else '🟡' if severity == 'NON_BREAKING' else '🟢'
                report.append(f"\n{icon} {severity} CHANGES ({len(severity_changes)}):")

                for change in severity_changes:
                    report.append(f"\n  • {change.description}")
                    report.append(f"    Field: {change.field_path}")
                    report.append(f"    Expected: {change.expected_value}")
                    report.append(f"    Actual: {change.actual_value}")
                    report.append(f"    💡 {change.suggestion}")

        # Auto-heal recommendation
        report.append(f"\n{'=' * 60}")
        if self.should_auto_heal(changes):
            report.append("✅ SAFE TO AUTO-HEAL - Changes are non-destructive")
        else:
            report.append("⚠️  MANUAL REVIEW REQUIRED - Contains breaking changes")

        return "\n".join(report)
