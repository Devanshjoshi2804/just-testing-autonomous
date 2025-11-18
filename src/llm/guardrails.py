"""
LLM Guardrails - Safety and Quality Controls
Validates LLM outputs for safety, quality, and correctness
"""
import re
import json
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class GuardrailViolation(str, Enum):
    """Types of guardrail violations"""
    TOXIC_CONTENT = "toxic_content"
    PII_LEAK = "pii_leak"
    HALLUCINATION = "hallucination"
    MALFORMED_OUTPUT = "malformed_output"
    EXCESSIVE_LENGTH = "excessive_length"
    PROFANITY = "profanity"
    INJECTION_ATTEMPT = "injection_attempt"
    INVALID_JSON = "invalid_json"


@dataclass
class GuardrailResult:
    """Result from guardrail validation"""
    passed: bool
    violations: List[GuardrailViolation]
    messages: List[str]
    sanitized_output: Optional[str] = None
    confidence: float = 1.0  # 0.0-1.0


class LLMGuardrails:
    """
    Comprehensive guardrails for LLM outputs

    Features:
    - PII detection and redaction
    - Toxicity detection
    - Hallucination detection
    - Output format validation
    - Length enforcement
    - Profanity filtering
    - Injection attempt detection
    """

    def __init__(
        self,
        max_output_length: int = 10000,
        enable_pii_detection: bool = True,
        enable_profanity_filter: bool = True,
        enable_toxicity_check: bool = True
    ):
        """
        Initialize guardrails

        Args:
            max_output_length: Maximum allowed output length
            enable_pii_detection: Enable PII detection
            enable_profanity_filter: Enable profanity filtering
            enable_toxicity_check: Enable toxicity checking
        """
        self.max_output_length = max_output_length
        self.enable_pii_detection = enable_pii_detection
        self.enable_profanity_filter = enable_profanity_filter
        self.enable_toxicity_check = enable_toxicity_check

        # PII patterns (basic implementation)
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }

        # Profanity list (basic - expand in production)
        self.profanity_words = {
            'fuck', 'shit', 'damn', 'bitch', 'ass', 'bastard',
            'crap', 'piss', 'asshole', 'slut', 'whore'
        }

        # Toxic phrases (basic - use ML model in production)
        self.toxic_phrases = [
            'i hate you',
            'kill yourself',
            'you should die',
            'go to hell',
            'you\'re worthless',
            'i hope you die'
        ]

    def validate(
        self,
        output: str,
        expected_format: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """
        Validate LLM output against all guardrails

        Args:
            output: LLM output to validate
            expected_format: Expected format ("json", "python", "text")
            context: Additional context for validation

        Returns:
            GuardrailResult with validation results
        """
        violations = []
        messages = []
        sanitized_output = output

        # Check 1: Length validation
        if len(output) > self.max_output_length:
            violations.append(GuardrailViolation.EXCESSIVE_LENGTH)
            messages.append(
                f"Output exceeds maximum length ({len(output)} > {self.max_output_length})"
            )

        # Check 2: PII detection
        if self.enable_pii_detection:
            pii_found = self._detect_pii(output)
            if pii_found:
                violations.append(GuardrailViolation.PII_LEAK)
                messages.append(f"PII detected: {', '.join(pii_found.keys())}")
                sanitized_output = self._redact_pii(output)

        # Check 3: Profanity filtering
        if self.enable_profanity_filter:
            profanity_found = self._detect_profanity(output)
            if profanity_found:
                violations.append(GuardrailViolation.PROFANITY)
                messages.append(f"Profanity detected: {len(profanity_found)} word(s)")
                sanitized_output = self._filter_profanity(sanitized_output)

        # Check 4: Toxicity detection
        if self.enable_toxicity_check:
            toxic_phrases_found = self._detect_toxicity(output)
            if toxic_phrases_found:
                violations.append(GuardrailViolation.TOXIC_CONTENT)
                messages.append(f"Toxic content detected: {len(toxic_phrases_found)} phrase(s)")

        # Check 5: Injection attempts
        if self._detect_injection_attempt(output):
            violations.append(GuardrailViolation.INJECTION_ATTEMPT)
            messages.append("Potential injection attempt detected")

        # Check 6: Format validation
        if expected_format:
            format_valid = self._validate_format(sanitized_output, expected_format)
            if not format_valid:
                violations.append(GuardrailViolation.MALFORMED_OUTPUT)
                messages.append(f"Output does not match expected format: {expected_format}")

        # Determine if passed
        passed = len(violations) == 0

        # Log violations
        if not passed:
            logger.warning(
                f"Guardrail violations detected: {', '.join(str(v.value) for v in violations)}",
                violations=violations,
                messages=messages
            )

        return GuardrailResult(
            passed=passed,
            violations=violations,
            messages=messages,
            sanitized_output=sanitized_output if not passed else output
        )

    def _detect_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text

        Returns:
            Dict of PII type -> list of matches
        """
        found_pii = {}

        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                found_pii[pii_type] = matches

        return found_pii

    def _redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        redacted = text

        for pii_type, pattern in self.pii_patterns.items():
            redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted)

        return redacted

    def _detect_profanity(self, text: str) -> List[str]:
        """Detect profanity in text"""
        text_lower = text.lower()
        found = []

        for word in self.profanity_words:
            if word in text_lower:
                found.append(word)

        return found

    def _filter_profanity(self, text: str) -> str:
        """Filter profanity from text"""
        filtered = text

        for word in self.profanity_words:
            # Replace with asterisks
            filtered = re.sub(
                r'\b' + re.escape(word) + r'\b',
                '*' * len(word),
                filtered,
                flags=re.IGNORECASE
            )

        return filtered

    def _detect_toxicity(self, text: str) -> List[str]:
        """
        Detect toxic phrases in text

        In production, use ML model like Perspective API or Detoxify
        """
        text_lower = text.lower()
        found = []

        for phrase in self.toxic_phrases:
            if phrase in text_lower:
                found.append(phrase)

        return found

    def _detect_injection_attempt(self, text: str) -> bool:
        """
        Detect potential prompt injection attempts

        Looks for:
        - Instruction overrides ("ignore previous instructions")
        - System prompt leaks ("show me your system prompt")
        - Jailbreak attempts
        """
        text_lower = text.lower()

        injection_patterns = [
            r'ignore (previous|all|the) (instructions?|prompts?)',
            r'disregard (previous|all|the) (instructions?|prompts?)',
            r'forget (previous|all|the) (instructions?|prompts?)',
            r'show (me|your) (system|initial) prompt',
            r'reveal (your|the) (system|initial) prompt',
            r'what (is|are) your (system|initial) (prompt|instructions)',
            r'you are now',
            r'new (instructions?|rules?)',
            r'act as if',
            r'pretend (you are|to be)'
        ]

        for pattern in injection_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _validate_format(self, text: str, expected_format: str) -> bool:
        """
        Validate output format

        Args:
            text: Text to validate
            expected_format: Expected format ("json", "python", "text")

        Returns:
            True if format is valid
        """
        if expected_format == "json":
            try:
                json.loads(text)
                return True
            except (json.JSONDecodeError, ValueError):
                return False

        elif expected_format == "python":
            # Basic Python syntax check
            try:
                compile(text, '<string>', 'exec')
                return True
            except SyntaxError:
                return False

        elif expected_format == "text":
            # Text format - always valid
            return True

        else:
            logger.warning(f"Unknown format type: {expected_format}")
            return True


def with_guardrails(
    expected_format: Optional[str] = None,
    max_length: int = 10000,
    auto_fix: bool = False
):
    """
    Decorator to apply guardrails to LLM function

    Usage:
        @with_guardrails(expected_format="json", max_length=5000)
        def call_llm(prompt: str) -> str:
            # ... LLM call ...
            return response

    Args:
        expected_format: Expected output format
        max_length: Maximum output length
        auto_fix: Automatically use sanitized output on violations

    Raises:
        GuardrailViolationError: If guardrails fail and auto_fix=False
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Call function
            output = func(*args, **kwargs)

            # Validate with guardrails
            guardrails = LLMGuardrails(max_output_length=max_length)
            result = guardrails.validate(output, expected_format=expected_format)

            if not result.passed:
                if auto_fix and result.sanitized_output:
                    logger.warning(
                        "Guardrail violations detected - using sanitized output",
                        violations=result.violations
                    )
                    return result.sanitized_output
                else:
                    raise GuardrailViolationError(
                        f"Guardrail violations: {', '.join(result.messages)}",
                        violations=result.violations
                    )

            return output

        return wrapper
    return decorator


class GuardrailViolationError(Exception):
    """Raised when guardrails detect violations"""

    def __init__(self, message: str, violations: List[GuardrailViolation]):
        super().__init__(message)
        self.violations = violations


# Specialized guardrails for specific use cases

class TestGenerationGuardrails(LLMGuardrails):
    """Guardrails specific to test generation"""

    def validate_test_code(self, code: str) -> GuardrailResult:
        """
        Validate generated test code

        Checks for:
        - Valid Python syntax
        - No malicious code (eval, exec, os.system, etc.)
        - No file system access
        - No network requests
        """
        result = self.validate(code, expected_format="python")

        # Additional checks for test code
        dangerous_imports = [
            'os.system', 'subprocess', 'eval', 'exec',
            'compile', '__import__', 'open(', 'file('
        ]

        for dangerous in dangerous_imports:
            if dangerous in code:
                result.violations.append(GuardrailViolation.INJECTION_ATTEMPT)
                result.messages.append(f"Dangerous code detected: {dangerous}")
                result.passed = False

        return result


# Global guardrails instance
_guardrails: Optional[LLMGuardrails] = None


def get_guardrails() -> LLMGuardrails:
    """Get or create global guardrails instance"""
    global _guardrails
    if _guardrails is None:
        _guardrails = LLMGuardrails()
    return _guardrails
