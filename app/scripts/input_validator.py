"""
Input validation and sanitization for Hugging Face models.

Prevents prompt injection and ensures safe input before passing to transformers.
"""

import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Validates and sanitizes input before passing to Hugging Face models.
    
    Protects against:
    - Prompt injection attempts
    - Control characters
    - Excessive special characters
    - Overly long inputs
    - Suspicious patterns
    """

    # Suspicious patterns that indicate injection attempts
    INJECTION_PATTERNS = [
        r"\\x[0-9a-fA-F]{2}",  # Hex escape sequences
        r"\\u[0-9a-fA-F]{4}",  # Unicode escape sequences
        r"<script",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
        r"SELECT\s+|INSERT\s+|UPDATE\s+|DELETE\s+",  # SQL keywords
        r"\$\{.*?\}",  # Template injection ${...}
        r"\{\{.*?\}\}",  # Template literals {{...}}
        r"__proto__",  # Prototype pollution
        r"constructor\s*\[",  # Constructor access
        r"eval\s*\(",  # Eval calls
        r"exec\s*\(",  # Exec calls
        r"import\s+os|import\s+sys|import\s+subprocess",  # Dangerous imports
        r"subprocess\.|os\.system|os\.popen",  # System commands
        r"<iframe|<embed|<object",  # Embedded content
        r"data:text/html",  # Data URIs
        r"vbscript:|data:",  # Dangerous protocols
    ]

    # Maximum allowed input length (characters, roughly 2000 tokens)
    MAX_INPUT_LENGTH = 8000  # ~2000 tokens at ~4 chars/token

    # Maximum special character ratio (15% is suspicious)
    MAX_SPECIAL_CHAR_RATIO = 0.15

    @staticmethod
    def validate(text: str, strict_mode: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate input for injection attacks and suspicious patterns.

        Args:
            text: Text to validate
            strict_mode: If True, reject suspicious content; if False, log warning only

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty input"

        # Check length
        if len(text) > InputValidator.MAX_INPUT_LENGTH:
            reason = f"Input too long ({len(text)} chars, max {InputValidator.MAX_INPUT_LENGTH})"
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        # Check for injection patterns
        for pattern in InputValidator.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = f"Detected suspicious pattern: {pattern}"
                logger.warning(f"Input validation failed: {reason}")
                if strict_mode:
                    return False, reason
                else:
                    logger.warning(f"Strict mode disabled; allowing content anyway")

        # Check for control characters (except newlines, tabs, carriage returns)
        control_chars = re.findall(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", text)
        if control_chars:
            reason = f"Detected {len(control_chars)} control characters"
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        # Check for excessive special characters (potential obfuscation)
        special_chars = len(re.findall(r"[^\w\s\.\,\-\:\!\?\'\"\(\)]", text))
        special_ratio = special_chars / len(text) if text else 0

        if special_ratio > InputValidator.MAX_SPECIAL_CHAR_RATIO:
            reason = f"Excessive special characters ({special_ratio:.1%}, max {InputValidator.MAX_SPECIAL_CHAR_RATIO:.1%})"
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        # Check for repeated suspicious sequences (potential obfuscation)
        # Look for 8+ consecutive special characters (allow common patterns like "...", "---", "===", "???")
        # Exclude common punctuation patterns and question marks (which are common in summaries)
        repeated_special = re.search(r"[^\w\s\.\,\-\:\!\?\'\"\(\)]{8,}", text)
        if repeated_special:
            reason = f"Detected repeated special characters: {repeated_special.group()[:20]}..."
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        return True, None

    @staticmethod
    def sanitize(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize input by removing dangerous patterns and truncating.

        Args:
            text: Text to sanitize
            max_length: Maximum length (uses MAX_INPUT_LENGTH if not provided)

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove control characters (except newlines, tabs, carriage returns)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

        # Remove null bytes
        text = text.replace("\x00", "")

        # Truncate to max length
        max_len = max_length or InputValidator.MAX_INPUT_LENGTH
        if len(text) > max_len:
            # Try to truncate at word boundary
            truncated = text[:max_len]
            last_space = truncated.rfind(" ")
            if last_space > max_len * 0.8:  # Only if we're not losing too much
                text = truncated[:last_space] + "..."
            else:
                text = truncated + "..."

        return text.strip()

    @staticmethod
    def validate_and_sanitize(text: str, strict_mode: bool = True) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and sanitize input in one step.

        Args:
            text: Text to validate and sanitize
            strict_mode: If True, reject suspicious content; if False, sanitize and allow

        Returns:
            Tuple of (is_valid, sanitized_text, reason_if_invalid)
        """
        # First sanitize
        sanitized = InputValidator.sanitize(text)

        # Then validate
        is_valid, reason = InputValidator.validate(sanitized, strict_mode=strict_mode)

        if not is_valid and strict_mode:
            return False, "", reason

        return True, sanitized, None


def validate_for_summarization(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function to validate text before summarization.

    Args:
        text: Text to validate

    Returns:
        Tuple of (is_valid, sanitized_text, reason_if_invalid)
    """
    return InputValidator.validate_and_sanitize(text, strict_mode=True)


def validate_for_video_ideas(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function to validate text before video idea generation.

    Args:
        text: Text to validate

    Returns:
        Tuple of (is_valid, sanitized_text, reason_if_invalid)
    """
    # Video ideas use template-based generation, so less strict
    # Just sanitize and allow (don't reject for validation failures)
    sanitized = InputValidator.sanitize(text)
    # Always return valid for video ideas (we sanitize but don't reject)
    return True, sanitized, None

