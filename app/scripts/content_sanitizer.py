"""
Content Sanitizer for AI News Tracker.

Implements Strategy 1: Pre-LLM Content Sanitation & Filtering

Cleans and sanitizes raw feed content before passing to LLM to:
1. Remove HTML, Markdown, and formatting noise
2. Strip boilerplate and promotional content
3. Truncate to reasonable token limits
4. Validate content for injection attacks and suspicious patterns
5. Enforce allowlist of safe content sources

Security Focus: Prevents prompt injection and content manipulation attacks.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)


class ContentSanitizer:
    """Sanitize and clean feed content before LLM processing."""

    # Suspicious patterns that indicate prompt injection attempts
    INJECTION_PATTERNS = [
        r"\\x[0-9a-fA-F]{2}",  # Hex escape sequences
        r"\\u[0-9a-fA-F]{4}",  # Unicode escape sequences
        r"<script",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
        r"SELECT\s+|INSERT\s+|UPDATE\s+|DELETE\s+",  # SQL keywords
        r"\$\{.*?\}",  # Template injection ${...}
        r"\{\{.*?\}\}",  # Template literals {{...}}
    ]

    # Common boilerplate patterns to remove
    BOILERPLATE_PATTERNS = [
        r"(read more|continue reading|full article|click here|view original)",
        r"(©|copyright|all rights reserved|published by)",
        r"(shared (on|via|from)|originally posted|cross-posted)",
        r"(image credit|photo by|illustration|diagram)",
        r"(advertisement|sponsored|promotional content|ad)",
        r"(updated|modified|last updated|posted on)",
    ]

    # Safe domains allowlist (can be extended)
    SAFE_DOMAINS = {
        "newsapi.org",
        "reddit.com",
        "twitter.com",
        "x.com",
        "github.com",
        "arxiv.org",
        "medium.com",
        "techcrunch.com",
        "wired.com",
        "theverge.com",
        "arstechnica.com",
        "nature.com",
        "science.org",
        "openai.com",
        "deepmind.com",
        "anthropic.com",
    }

    def __init__(self, max_tokens: int = 2000, strict_mode: bool = True):
        """
        Initialize ContentSanitizer.

        Args:
            max_tokens: Maximum tokens allowed per article (default 2000)
            strict_mode: If True, reject suspicious content; if False, log warning only
        """
        self.max_tokens = max_tokens
        self.strict_mode = strict_mode

    def remove_html_markdown(self, text: str) -> str:
        """
        Remove HTML tags and Markdown formatting from text.

        Args:
            text: Raw text with HTML/Markdown

        Returns:
            Cleaned text with formatting removed
        """
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove HTML entities
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#39;", "'", text)

        # Remove Markdown syntax
        text = re.sub(r"#+\s+", "", text)  # Headers (#, ##, ###)
        text = re.sub(r"\*\*|__", "", text)  # Bold
        text = re.sub(r"\*|_", "", text)  # Italic
        text = re.sub(r"~~", "", text)  # Strikethrough
        text = re.sub(r"`{1,3}", "", text)  # Code blocks
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # Links [text](url)
        text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", text)  # Images ![alt](url)

        # Remove ANSI color codes
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def remove_boilerplate(self, text: str) -> str:
        """
        Remove common boilerplate text and promotional content.

        Args:
            text: Text with potential boilerplate

        Returns:
            Text with boilerplate removed
        """
        if not text:
            return ""

        # Case-insensitive removal of boilerplate patterns
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove common footer sentences
        footer_patterns = [
            r"For more information.*?(?:$|\.)",
            r"Follow us on.*?(?:$|\.)",
            r"Subscribe to our.*?(?:$|\.)",
            r"If you found this helpful.*?(?:$|\.)",
        ]
        for pattern in footer_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Normalize whitespace again
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def truncate_by_tokens(self, text: str, max_tokens: Optional[int] = None) -> str:
        """
        Truncate text to approximate token limit while preserving meaning.

        Strategy: Keep first paragraph + last paragraph if text is too long.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens (uses self.max_tokens if not provided)

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text:
            return ""

        max_tokens = max_tokens or self.max_tokens

        # Rough token estimation: 1 token ≈ 4 characters
        # (This is a simplified estimate; tiktoken would be more accurate)
        max_chars = max_tokens * 4

        if len(text) <= max_chars:
            return text

        # Split into paragraphs
        paragraphs = text.split("\n\n")

        if not paragraphs:
            return text[:max_chars] + "..."

        # Try to keep first + last paragraphs
        first_para = paragraphs[0]
        last_para = paragraphs[-1]

        combined = first_para + "\n\n[...]\n\n" + last_para

        if len(combined) <= max_chars:
            return combined

        # Fallback: just truncate at character limit
        return text[:max_chars] + "..."

    def validate_content(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate content for injection attacks and suspicious patterns.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not text:
            return False, "Empty content"

        # Check for injection patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = f"Detected suspicious pattern: {pattern}"
                logger.warning(f"Content validation failed: {reason}")
                if self.strict_mode:
                    return False, reason
                else:
                    logger.warning(f"Strict mode disabled; allowing content anyway")

        # Check for excessive special characters (potential obfuscation)
        special_chars = len(re.findall(r"[^\w\s\.\,\-\:\!\?]", text))
        special_ratio = special_chars / len(text) if text else 0

        if special_ratio > 0.15:  # More than 15% special chars is suspicious
            reason = f"Excessive special characters ({special_ratio:.1%})"
            logger.warning(f"Content validation failed: {reason}")
            if self.strict_mode:
                return False, reason

        # Check for control characters
        if re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", text):
            reason = "Detected control characters"
            logger.warning(f"Content validation failed: {reason}")
            if self.strict_mode:
                return False, reason

        return True, None

    def validate_source_domain(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that source URL is from a safe/trusted domain.

        Args:
            url: Source URL to validate

        Returns:
            Tuple of (is_safe, reason_if_not_safe)
        """
        if not url:
            return False, "No source URL provided"

        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Remove www. prefix for comparison
            if domain.startswith("www."):
                domain = domain[4:]

            # Check if domain is in allowlist
            if domain in self.SAFE_DOMAINS:
                return True, None

            # Check if it's a subdomain of an allowed domain
            for safe_domain in self.SAFE_DOMAINS:
                if domain.endswith("." + safe_domain):
                    return True, None

            reason = f"Domain '{domain}' not in allowlist"
            logger.warning(f"Source validation failed: {reason}")
            if self.strict_mode:
                return False, reason
            else:
                logger.warning("Strict mode disabled; allowing domain anyway")
                return True, None

        except Exception as e:
            reason = f"Failed to parse URL: {str(e)}"
            logger.error(reason)
            return False, reason

    def sanitize_feed_item(self, item: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Orchestrate full sanitization pipeline for a feed item.

        Args:
            item: Feed item dict with keys: title, body, source, url

        Returns:
            Sanitized item dict, or None if validation failed
        """
        if not item:
            logger.warning("Empty feed item")
            return None

        try:
            # Validate source domain
            source_url = item.get("url", "")
            is_safe, reason = self.validate_source_domain(source_url)
            if not is_safe:
                logger.warning(f"Rejecting item from {source_url}: {reason}")
                return None

            # Sanitize title
            title = item.get("title", "").strip()
            if title:
                title = self.remove_html_markdown(title)
                title = self.remove_boilerplate(title)
            else:
                logger.warning("Feed item missing title")

            # Sanitize body
            body = item.get("body", "").strip()
            if body:
                body = self.remove_html_markdown(body)
                body = self.remove_boilerplate(body)
                body = self.truncate_by_tokens(body, self.max_tokens)

                # Validate body content
                is_valid, reason = self.validate_content(body)
                if not is_valid:
                    logger.warning(f"Rejecting item: {reason}")
                    return None
            else:
                logger.warning("Feed item missing body")

            # Return sanitized item
            sanitized = {
                "title": title,
                "body": body,
                "source": item.get("source", "Unknown"),
                "url": source_url,
            }

            logger.debug(f"Successfully sanitized item: {title[:50]}...")
            return sanitized

        except Exception as e:
            logger.error(f"Error sanitizing feed item: {str(e)}", exc_info=True)
            return None

    def sanitize_batch(
        self, items: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Sanitize a batch of feed items.

        Args:
            items: List of feed item dicts

        Returns:
            List of sanitized items (failed items filtered out)
        """
        sanitized_items = []

        for item in items:
            sanitized = self.sanitize_feed_item(item)
            if sanitized:
                sanitized_items.append(sanitized)

        logger.info(
            f"Sanitized {len(sanitized_items)} out of {len(items)} items "
            f"({100 * len(sanitized_items) / len(items):.1f}% pass rate)"
        )

        return sanitized_items


# Convenience functions for direct usage
def sanitize_text(text: str, max_tokens: int = 2000) -> str:
    """
    Quick sanitization of raw text.

    Args:
        text: Raw text to sanitize
        max_tokens: Maximum tokens

    Returns:
        Sanitized text
    """
    sanitizer = ContentSanitizer(max_tokens=max_tokens)
    text = sanitizer.remove_html_markdown(text)
    text = sanitizer.remove_boilerplate(text)
    text = sanitizer.truncate_by_tokens(text, max_tokens)
    return text


def validate_feed_item(item: Dict[str, str]) -> bool:
    """
    Quick validation of a feed item.

    Args:
        item: Feed item dict

    Returns:
        True if valid, False otherwise
    """
    sanitizer = ContentSanitizer(strict_mode=True)
    sanitized = sanitizer.sanitize_feed_item(item)
    return sanitized is not None
