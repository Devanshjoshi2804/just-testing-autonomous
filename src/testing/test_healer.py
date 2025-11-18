"""
Test Healer - Self-Healing Tests
Automatically updates test expectations when APIs change
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import copy

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

from src.analysis.change_detector import ChangeDetector, APIChange


@dataclass
class HealingAction:
    """Represents a test healing action"""
    action_type: str  # 'update_status', 'update_field', 'add_field', 'remove_field'
    field_path: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: datetime


class TestHealer:
    """
    Automatically heals tests when APIs change

    Healing strategies:
    1. Update expected status codes
    2. Update expected field values
    3. Add new optional fields
    4. Remove obsolete fields
    5. Update field types
    """

    def __init__(self, auto_heal: bool = True, require_confirmation: bool = False):
        """
        Initialize TestHealer

        Args:
            auto_heal: Automatically heal safe changes
            require_confirmation: Require manual confirmation before healing
        """
        self.auto_heal = auto_heal
        self.require_confirmation = require_confirmation
        self.change_detector = ChangeDetector()
        self.healing_history = []

        logger.info(
            f"TestHealer initialized "
            f"(auto_heal={auto_heal}, require_confirmation={require_confirmation})"
        )

    def heal_test(
        self,
        test: Dict[str, Any],
        actual_response: Dict[str, Any],
        changes: Optional[List[APIChange]] = None
    ) -> Dict[str, Any]:
        """
        Heal a test based on detected API changes

        Args:
            test: Original test specification
            actual_response: Actual API response
            changes: Optional list of detected changes (will detect if not provided)

        Returns:
            Healed test specification
        """
        # Detect changes if not provided
        if changes is None:
            expected_response = {
                'status_code': test.get('expected_status', 200),
                'body': test.get('expected_response', {})
            }
            changes = self.change_detector.detect_changes(
                expected_response,
                actual_response,
                test
            )

        if not changes:
            logger.debug("No changes detected - no healing needed")
            return test

        # Check if safe to auto-heal
        safe_to_heal = self.change_detector.should_auto_heal(changes)

        if not safe_to_heal and not self.require_confirmation:
            logger.warning(
                f"Breaking changes detected in test '{test.get('name', 'unknown')}' - "
                "manual review recommended"
            )
            # Don't auto-heal breaking changes without confirmation
            return test

        # Create healed test
        healed_test = copy.deepcopy(test)
        actions = []

        # Apply healing actions
        for change in changes:
            action = self._apply_healing_action(healed_test, change, actual_response)
            if action:
                actions.append(action)

        # Store healing history
        if actions:
            self.healing_history.append({
                'test_name': test.get('name', 'unknown'),
                'endpoint': test.get('endpoint', 'unknown'),
                'changes': changes,
                'actions': actions,
                'timestamp': datetime.now(),
                'safe_heal': safe_to_heal
            })

            logger.info(
                f"✨ Healed test '{test.get('name', 'unknown')}' - "
                f"Applied {len(actions)} healing actions"
            )

        return healed_test

    def _apply_healing_action(
        self,
        test: Dict[str, Any],
        change: APIChange,
        actual_response: Dict[str, Any]
    ) -> Optional[HealingAction]:
        """
        Apply a single healing action to a test

        Args:
            test: Test to modify (modified in-place)
            change: Detected change
            actual_response: Actual API response

        Returns:
            HealingAction if action was applied, None otherwise
        """
        action = None

        # 1. Heal status code changes
        if change.change_type == 'status_code':
            old_status = test.get('expected_status', 200)
            new_status = change.actual_value

            test['expected_status'] = new_status

            action = HealingAction(
                action_type='update_status',
                field_path='expected_status',
                old_value=old_status,
                new_value=new_status,
                reason=change.description,
                timestamp=datetime.now()
            )

        # 2. Heal field additions (add to expected response)
        elif change.change_type == 'field_added':
            # Add new field to expected response
            if 'expected_response' not in test:
                test['expected_response'] = {}

            self._set_nested_field(
                test['expected_response'],
                change.field_path,
                change.actual_value
            )

            action = HealingAction(
                action_type='add_field',
                field_path=change.field_path,
                old_value=None,
                new_value=change.actual_value,
                reason=change.description,
                timestamp=datetime.now()
            )

        # 3. Heal field removals (remove from expected response)
        elif change.change_type == 'field_removed':
            if 'expected_response' in test:
                self._remove_nested_field(
                    test['expected_response'],
                    change.field_path
                )

                action = HealingAction(
                    action_type='remove_field',
                    field_path=change.field_path,
                    old_value=change.expected_value,
                    new_value=None,
                    reason=change.description,
                    timestamp=datetime.now()
                )

        # 4. Heal type changes (update expected type)
        elif change.change_type == 'type_changed' or change.change_type == 'field_now_populated':
            if 'expected_response' in test:
                self._set_nested_field(
                    test['expected_response'],
                    change.field_path,
                    change.actual_value
                )

                action = HealingAction(
                    action_type='update_field',
                    field_path=change.field_path,
                    old_value=change.expected_value,
                    new_value=change.actual_value,
                    reason=change.description,
                    timestamp=datetime.now()
                )

        # 5. Heal value changes (update expected value)
        elif change.change_type == 'value_changed':
            # Only heal if marked as structural
            if change.severity in ['BREAKING', 'NON_BREAKING']:
                if 'expected_response' in test:
                    self._set_nested_field(
                        test['expected_response'],
                        change.field_path,
                        change.actual_value
                    )

                    action = HealingAction(
                        action_type='update_field',
                        field_path=change.field_path,
                        old_value=change.expected_value,
                        new_value=change.actual_value,
                        reason=change.description,
                        timestamp=datetime.now()
                    )

        return action

    def _set_nested_field(self, obj: Dict, path: str, value: Any):
        """Set a nested field using dot notation"""
        parts = path.split('.')
        current = obj

        # Navigate to parent
        for part in parts[:-1]:
            # Handle array indices like "items[0]"
            if '[' in part:
                field, index = part.split('[')
                index = int(index.rstrip(']'))

                if field not in current:
                    current[field] = []

                # Ensure list is long enough
                while len(current[field]) <= index:
                    current[field].append({})

                current = current[field][index]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Set final value
        final_part = parts[-1]
        if '[' in final_part:
            field, index = final_part.split('[')
            index = int(index.rstrip(']'))

            if field not in current:
                current[field] = []

            while len(current[field]) <= index:
                current[field].append(None)

            current[field][index] = value
        else:
            current[final_part] = value

    def _remove_nested_field(self, obj: Dict, path: str):
        """Remove a nested field using dot notation"""
        parts = path.split('.')
        current = obj

        # Navigate to parent
        for part in parts[:-1]:
            if '[' in part:
                field, index = part.split('[')
                index = int(index.rstrip(']'))
                current = current[field][index]
            else:
                if part not in current:
                    return
                current = current[part]

        # Remove final field
        final_part = parts[-1]
        if final_part in current:
            del current[final_part]

    def get_healing_report(self, test_name: Optional[str] = None) -> str:
        """Generate healing history report"""
        if not self.healing_history:
            return "No healing actions recorded"

        # Filter by test name if provided
        history = self.healing_history
        if test_name:
            history = [h for h in history if h['test_name'] == test_name]

        if not history:
            return f"No healing actions for test '{test_name}'"

        report = []
        report.append("\n✨ TEST HEALING REPORT")
        report.append("=" * 60)
        report.append(f"Total healing sessions: {len(history)}\n")

        for session in history:
            report.append(f"\nTest: {session['test_name']}")
            report.append(f"Endpoint: {session['endpoint']}")
            report.append(f"Timestamp: {session['timestamp']}")
            report.append(f"Safe Heal: {'✅' if session['safe_heal'] else '⚠️'}")
            report.append(f"Changes: {len(session['changes'])}")
            report.append(f"Actions: {len(session['actions'])}")

            for action in session['actions']:
                report.append(f"\n  {action.action_type.upper()}:")
                report.append(f"    Field: {action.field_path}")
                report.append(f"    Old: {action.old_value}")
                report.append(f"    New: {action.new_value}")
                report.append(f"    Reason: {action.reason}")

        report.append("\n" + "=" * 60)
        return "\n".join(report)

    def export_healing_history(self) -> List[Dict[str, Any]]:
        """Export healing history as JSON-serializable dict"""
        return [{
            'test_name': h['test_name'],
            'endpoint': h['endpoint'],
            'timestamp': h['timestamp'].isoformat(),
            'safe_heal': h['safe_heal'],
            'changes': [{
                'type': c.change_type,
                'severity': c.severity,
                'field': c.field_path,
                'expected': str(c.expected_value),
                'actual': str(c.actual_value),
                'description': c.description
            } for c in h['changes']],
            'actions': [{
                'type': a.action_type,
                'field': a.field_path,
                'old_value': str(a.old_value),
                'new_value': str(a.new_value),
                'reason': a.reason,
                'timestamp': a.timestamp.isoformat()
            } for a in h['actions']]
        } for h in self.healing_history]

    def clear_history(self):
        """Clear healing history"""
        self.healing_history = []
        logger.info("Healing history cleared")
