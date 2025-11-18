"""
Constraint Extractor - Extract validation rules from API documentation
Analyzes documentation to discover parameter constraints: min/max, formats, enums, dependencies
"""
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ConstraintType(str, Enum):
    """Types of constraints"""
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    ENUM = "enum"
    FORMAT = "format"
    REQUIRED = "required"
    DEPENDENCY = "dependency"  # If A is set, B is required
    MUTUAL_EXCLUSION = "mutual_exclusion"  # A and B cannot both be set


@dataclass
class ParameterConstraint:
    """Constraint on a single parameter"""
    param_name: str
    constraint_type: ConstraintType
    value: Any
    description: str = ""
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class ParameterConstraints:
    """All constraints for a parameter"""
    name: str
    type: str  # string, integer, number, boolean, array, object
    required: bool = False
    constraints: List[ParameterConstraint] = field(default_factory=list)
    description: str = ""
    example_values: List[Any] = field(default_factory=list)

    def get_constraint(self, constraint_type: ConstraintType) -> Optional[ParameterConstraint]:
        """Get constraint by type"""
        for c in self.constraints:
            if c.constraint_type == constraint_type:
                return c
        return None

    def has_constraint(self, constraint_type: ConstraintType) -> bool:
        """Check if has constraint"""
        return self.get_constraint(constraint_type) is not None


class ConstraintExtractor:
    """
    Extracts validation constraints from API documentation

    Analyzes documentation text to discover:
    - Min/max length for strings
    - Min/max value for numbers
    - Regex patterns
    - Enum values
    - Format requirements (email, URL, UUID, date, etc.)
    - Required vs optional
    - Parameter dependencies
    """

    def __init__(self):
        # Regex patterns for constraint extraction
        self.patterns = {
            # Numeric constraints
            'min_value': [
                r'(?:minimum|min|at least|greater than or equal to|>=)\s*[:\s]*(\d+)',
                r'(?:must be|should be)\s+(?:at least|minimum of)\s+(\d+)',
            ],
            'max_value': [
                r'(?:maximum|max|at most|less than or equal to|<=)\s*[:\s]*(\d+)',
                r'(?:must be|should be)\s+(?:at most|maximum of)\s+(\d+)',
            ],
            'range': [
                r'(?:between|range)\s+(\d+)\s+(?:and|to|-)\s+(\d+)',
            ],

            # String length constraints
            'min_length': [
                r'(?:minimum length|min length)\s*[:\s]*(\d+)',
                r'at least (\d+) characters?',
            ],
            'max_length': [
                r'(?:maximum length|max length)\s*[:\s]*(\d+)',
                r'up to (\d+) characters?',
                r'no more than (\d+) characters?',
            ],

            # Format patterns
            'email': [
                r'(?:email|e-mail)\s+(?:address|format)',
                r'must be (?:a )?valid email',
            ],
            'url': [
                r'(?:URL|url|uri)\s*(?:format)?',
                r'must be (?:a )?valid (?:URL|url)',
            ],
            'uuid': [
                r'(?:UUID|uuid|GUID)\s*(?:format)?',
                r'must be (?:a )?valid (?:UUID|uuid)',
            ],
            'date': [
                r'(?:date|Date)\s*(?:format)?',
                r'ISO\s*8601',
                r'YYYY-MM-DD',
            ],
            'datetime': [
                r'(?:datetime|timestamp)\s*(?:format)?',
                r'ISO\s*8601.*(?:datetime|timestamp)',
            ],

            # Enum values
            'enum': [
                r'(?:one of|must be one of|valid values are|allowed values)[:\s]+([^.]+)',
                r'(?:enum|enumeration)[:\s]+([^.]+)',
            ],

            # Required/Optional
            'required': [
                r'required',
                r'mandatory',
                r'must (?:be )?(?:provide|specify|include)',
            ],
            'optional': [
                r'optional',
                r'not required',
                r'may (?:be )?(?:provide|specify|include)',
            ],

            # Dependencies
            'dependency': [
                r'if\s+(\w+)\s+is\s+(?:set|provided|specified),?\s+(?:then\s+)?(\w+)\s+(?:is\s+)?(?:required|must be provided)',
                r'requires?\s+(\w+)\s+when\s+(\w+)\s+is\s+(?:set|provided)',
            ],
        }

    def extract_constraints(
        self,
        endpoint: Dict[str, Any],
        documentation: str = ""
    ) -> Dict[str, ParameterConstraints]:
        """
        Extract all constraints for an endpoint

        Args:
            endpoint: Endpoint dict with parameters
            documentation: Full documentation text for this endpoint

        Returns:
            Dict mapping parameter name to its constraints
        """
        constraints_map = {}

        parameters = endpoint.get('parameters', [])

        for param in parameters:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')
            param_required = param.get('required', False)
            param_desc = param.get('description', '')

            # Initialize constraints for this parameter
            param_constraints = ParameterConstraints(
                name=param_name,
                type=param_type,
                required=param_required,
                description=param_desc
            )

            # Extract constraints from parameter definition
            self._extract_from_parameter(param, param_constraints)

            # Extract constraints from documentation text
            if documentation:
                self._extract_from_documentation(
                    param_name,
                    documentation,
                    param_constraints
                )

            constraints_map[param_name] = param_constraints

        return constraints_map

    def _extract_from_parameter(
        self,
        param: Dict[str, Any],
        param_constraints: ParameterConstraints
    ):
        """Extract constraints from parameter definition (OpenAPI schema)"""

        # Direct schema properties
        if 'minimum' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.MIN_VALUE,
                    value=param['minimum'],
                    confidence=1.0
                )
            )

        if 'maximum' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.MAX_VALUE,
                    value=param['maximum'],
                    confidence=1.0
                )
            )

        if 'minLength' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.MIN_LENGTH,
                    value=param['minLength'],
                    confidence=1.0
                )
            )

        if 'maxLength' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.MAX_LENGTH,
                    value=param['maxLength'],
                    confidence=1.0
                )
            )

        if 'pattern' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.PATTERN,
                    value=param['pattern'],
                    confidence=1.0
                )
            )

        if 'enum' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.ENUM,
                    value=param['enum'],
                    confidence=1.0
                )
            )

        if 'format' in param:
            param_constraints.constraints.append(
                ParameterConstraint(
                    param_name=param_constraints.name,
                    constraint_type=ConstraintType.FORMAT,
                    value=param['format'],
                    confidence=1.0
                )
            )

        # Example values
        if 'example' in param:
            param_constraints.example_values.append(param['example'])

        if 'examples' in param:
            param_constraints.example_values.extend(param['examples'])

    def _extract_from_documentation(
        self,
        param_name: str,
        documentation: str,
        param_constraints: ParameterConstraints
    ):
        """Extract constraints from documentation text"""

        # Find section about this parameter
        param_section = self._find_parameter_section(param_name, documentation)
        if not param_section:
            return

        # Extract numeric constraints
        self._extract_numeric_constraints(param_name, param_section, param_constraints)

        # Extract string length constraints
        self._extract_length_constraints(param_name, param_section, param_constraints)

        # Extract format constraints
        self._extract_format_constraints(param_name, param_section, param_constraints)

        # Extract enum values
        self._extract_enum_constraints(param_name, param_section, param_constraints)

        # Extract required/optional
        self._extract_required_constraints(param_name, param_section, param_constraints)

    def _find_parameter_section(self, param_name: str, documentation: str) -> str:
        """Find documentation section for a specific parameter"""
        lines = documentation.split('\n')

        # Look for parameter name in documentation
        param_section_lines = []
        in_section = False

        for line in lines:
            # Check if line mentions parameter
            if param_name in line:
                in_section = True
                param_section_lines.append(line)
            elif in_section:
                # Continue collecting until we hit another parameter or section
                if re.match(r'^\s*[-*]\s+\w+[:\s]', line):  # Looks like another parameter
                    break
                if re.match(r'^#{1,4}\s+', line):  # Looks like a heading
                    break
                param_section_lines.append(line)

                # Stop after a few lines if we've moved on
                if len(param_section_lines) > 10:
                    break

        return '\n'.join(param_section_lines)

    def _extract_numeric_constraints(
        self,
        param_name: str,
        text: str,
        param_constraints: ParameterConstraints
    ):
        """Extract min/max numeric constraints"""

        # Min value
        for pattern in self.patterns['min_value']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_val = int(match.group(1))
                    if not param_constraints.has_constraint(ConstraintType.MIN_VALUE):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MIN_VALUE,
                                value=min_val,
                                confidence=0.8
                            )
                        )
                except (ValueError, IndexError):
                    pass

        # Max value
        for pattern in self.patterns['max_value']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    max_val = int(match.group(1))
                    if not param_constraints.has_constraint(ConstraintType.MAX_VALUE):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MAX_VALUE,
                                value=max_val,
                                confidence=0.8
                            )
                        )
                except (ValueError, IndexError):
                    pass

        # Range (both min and max)
        for pattern in self.patterns['range']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_val = int(match.group(1))
                    max_val = int(match.group(2))

                    if not param_constraints.has_constraint(ConstraintType.MIN_VALUE):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MIN_VALUE,
                                value=min_val,
                                confidence=0.9
                            )
                        )

                    if not param_constraints.has_constraint(ConstraintType.MAX_VALUE):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MAX_VALUE,
                                value=max_val,
                                confidence=0.9
                            )
                        )
                except (ValueError, IndexError):
                    pass

    def _extract_length_constraints(
        self,
        param_name: str,
        text: str,
        param_constraints: ParameterConstraints
    ):
        """Extract string length constraints"""

        # Min length
        for pattern in self.patterns['min_length']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_len = int(match.group(1))
                    if not param_constraints.has_constraint(ConstraintType.MIN_LENGTH):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MIN_LENGTH,
                                value=min_len,
                                confidence=0.8
                            )
                        )
                except (ValueError, IndexError):
                    pass

        # Max length
        for pattern in self.patterns['max_length']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    max_len = int(match.group(1))
                    if not param_constraints.has_constraint(ConstraintType.MAX_LENGTH):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.MAX_LENGTH,
                                value=max_len,
                                confidence=0.8
                            )
                        )
                except (ValueError, IndexError):
                    pass

    def _extract_format_constraints(
        self,
        param_name: str,
        text: str,
        param_constraints: ParameterConstraints
    ):
        """Extract format constraints (email, URL, UUID, etc.)"""

        formats = ['email', 'url', 'uuid', 'date', 'datetime']

        for fmt in formats:
            for pattern in self.patterns[fmt]:
                if re.search(pattern, text, re.IGNORECASE):
                    if not param_constraints.has_constraint(ConstraintType.FORMAT):
                        param_constraints.constraints.append(
                            ParameterConstraint(
                                param_name=param_name,
                                constraint_type=ConstraintType.FORMAT,
                                value=fmt,
                                confidence=0.9
                            )
                        )
                    break

    def _extract_enum_constraints(
        self,
        param_name: str,
        text: str,
        param_constraints: ParameterConstraints
    ):
        """Extract enum values"""

        for pattern in self.patterns['enum']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                enum_text = match.group(1)

                # Parse enum values
                # Common formats: "value1, value2, value3" or "value1|value2|value3"
                enum_values = re.split(r'[,|]', enum_text)
                enum_values = [
                    v.strip().strip('"\'`')
                    for v in enum_values
                    if v.strip()
                ]

                if enum_values and not param_constraints.has_constraint(ConstraintType.ENUM):
                    param_constraints.constraints.append(
                        ParameterConstraint(
                            param_name=param_name,
                            constraint_type=ConstraintType.ENUM,
                            value=enum_values,
                            confidence=0.7
                        )
                    )

    def _extract_required_constraints(
        self,
        param_name: str,
        text: str,
        param_constraints: ParameterConstraints
    ):
        """Extract required/optional status"""

        # Check for "required" indicators
        is_required = False
        for pattern in self.patterns['required']:
            if re.search(pattern, text, re.IGNORECASE):
                is_required = True
                break

        # Check for "optional" indicators
        is_optional = False
        for pattern in self.patterns['optional']:
            if re.search(pattern, text, re.IGNORECASE):
                is_optional = True
                break

        # Update required status (only if not already set and we found evidence)
        if is_required and not is_optional:
            param_constraints.required = True
        elif is_optional and not is_required:
            param_constraints.required = False

    def get_constraint_summary(
        self,
        constraints_map: Dict[str, ParameterConstraints]
    ) -> Dict[str, Any]:
        """Get summary of extracted constraints"""

        total_params = len(constraints_map)
        params_with_constraints = sum(
            1 for c in constraints_map.values()
            if c.constraints
        )

        constraint_type_counts = {}
        for param_constraints in constraints_map.values():
            for constraint in param_constraints.constraints:
                ct = constraint.constraint_type
                constraint_type_counts[ct] = constraint_type_counts.get(ct, 0) + 1

        return {
            'total_parameters': total_params,
            'parameters_with_constraints': params_with_constraints,
            'coverage': (params_with_constraints / total_params * 100) if total_params > 0 else 0,
            'constraint_type_counts': constraint_type_counts,
            'parameters': {
                name: {
                    'type': c.type,
                    'required': c.required,
                    'constraint_count': len(c.constraints),
                    'constraints': [
                        {
                            'type': con.constraint_type,
                            'value': con.value,
                            'confidence': con.confidence
                        }
                        for con in c.constraints
                    ]
                }
                for name, c in constraints_map.items()
            }
        }
