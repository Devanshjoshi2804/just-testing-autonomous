"""
Constraint Updater
Updates parameter constraints based on learned information
"""
from typing import Dict, Any, Optional
from copy import deepcopy

try:
    from loguru import logger
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): pass
        def warning(self, msg, **kwargs): pass
        def error(self, msg, **kwargs): pass
        def debug(self, msg, **kwargs): pass
    logger = MockLogger()


class ConstraintUpdater:
    """
    Update parameter constraints with learned information

    Merges learned constraints with existing constraints:
    - Adds new constraints that don't exist
    - Updates existing constraints if learned values are more restrictive
    - Maintains confidence scores
    - Tracks update history
    """

    def __init__(self):
        """Initialize constraint updater"""
        self.update_history = []

    def update_constraints(
        self,
        existing_constraints: Dict[str, Dict[str, Any]],
        learned_constraints: Dict[str, Dict[str, Any]],
        merge_strategy: str = 'conservative'
    ) -> Dict[str, Dict[str, Any]]:
        """
        Update constraints with learned information

        Args:
            existing_constraints: Current parameter constraints
            learned_constraints: Learned constraints from errors
            merge_strategy: How to merge ('conservative', 'aggressive', 'replace')
                - conservative: Only add new constraints, don't modify existing
                - aggressive: Update existing constraints with learned values
                - replace: Replace existing with learned

        Returns:
            Updated constraints dict
        """
        updated = deepcopy(existing_constraints)

        for field_name, learned in learned_constraints.items():
            if field_name not in updated:
                # New field - add all learned constraints
                updated[field_name] = learned
                self._log_update('add_new_field', field_name, learned)

            else:
                # Field exists - merge constraints
                if merge_strategy == 'replace':
                    updated[field_name] = learned
                    self._log_update('replace_field', field_name, learned)

                elif merge_strategy == 'aggressive':
                    updated[field_name] = self._merge_aggressive(
                        updated[field_name],
                        learned,
                        field_name
                    )

                else:  # conservative
                    updated[field_name] = self._merge_conservative(
                        updated[field_name],
                        learned,
                        field_name
                    )

        return updated

    def _merge_conservative(
        self,
        existing: Dict[str, Any],
        learned: Dict[str, Any],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Conservative merge - only add new constraints

        Args:
            existing: Existing constraints for field
            learned: Learned constraints for field
            field_name: Name of the field

        Returns:
            Merged constraints
        """
        merged = deepcopy(existing)

        for key, value in learned.items():
            if key not in merged:
                # New constraint - add it
                merged[key] = value
                self._log_update('add_constraint', field_name, {key: value})

            # If exists, don't modify (conservative)

        return merged

    def _merge_aggressive(
        self,
        existing: Dict[str, Any],
        learned: Dict[str, Any],
        field_name: str
    ) -> Dict[str, Any]:
        """
        Aggressive merge - update with more restrictive values

        Args:
            existing: Existing constraints for field
            learned: Learned constraints for field
            field_name: Name of the field

        Returns:
            Merged constraints
        """
        merged = deepcopy(existing)

        for key, value in learned.items():
            if key not in merged:
                # New constraint - add it
                merged[key] = value
                self._log_update('add_constraint', field_name, {key: value})

            else:
                # Constraint exists - check if learned is more restrictive
                updated = self._merge_value(key, merged[key], value)

                if updated != merged[key]:
                    merged[key] = updated
                    self._log_update(
                        'update_constraint',
                        field_name,
                        {key: {'old': merged[key], 'new': updated}}
                    )

        return merged

    def _merge_value(self, constraint_type: str, existing_value: Any, learned_value: Any) -> Any:
        """
        Merge a single constraint value

        Takes the more restrictive value:
        - For min: take larger value
        - For max: take smaller value
        - For required: True if either is True
        - For enum: intersection of values
        - For format/type: keep existing (more likely to be accurate)
        """

        # Minimum - take larger
        if constraint_type in ['min', 'minimum', 'min_length']:
            if isinstance(existing_value, (int, float)) and isinstance(learned_value, (int, float)):
                return max(existing_value, learned_value)

        # Maximum - take smaller
        elif constraint_type in ['max', 'maximum', 'max_length']:
            if isinstance(existing_value, (int, float)) and isinstance(learned_value, (int, float)):
                return min(existing_value, learned_value)

        # Required - True if either is True
        elif constraint_type == 'required':
            return existing_value or learned_value

        # Enum - intersection
        elif constraint_type == 'enum':
            if isinstance(existing_value, list) and isinstance(learned_value, list):
                intersection = list(set(existing_value) & set(learned_value))
                # If intersection is empty, keep existing (safer)
                return intersection if intersection else existing_value

        # Format/Type - keep existing (more likely accurate from docs)
        elif constraint_type in ['format', 'type']:
            return existing_value

        # Pattern - keep existing
        elif constraint_type == 'pattern':
            return existing_value

        # Default - keep existing
        return existing_value

    def _log_update(self, update_type: str, field_name: str, details: Any):
        """Log an update to history"""
        entry = {
            'type': update_type,
            'field': field_name,
            'details': details
        }

        self.update_history.append(entry)
        logger.info(f"Constraint update: {update_type} for {field_name}")

    def get_update_summary(self) -> Dict[str, Any]:
        """Get summary of updates made"""
        summary = {
            'total_updates': len(self.update_history),
            'by_type': {},
            'fields_affected': set()
        }

        for entry in self.update_history:
            update_type = entry['type']
            summary['by_type'][update_type] = summary['by_type'].get(update_type, 0) + 1
            summary['fields_affected'].add(entry['field'])

        summary['fields_affected'] = list(summary['fields_affected'])

        return summary

    def export_update_history(self) -> list:
        """Export full update history"""
        return self.update_history.copy()

    def clear_history(self):
        """Clear update history"""
        self.update_history = []
