"""
Guardrails for AI News Tracker - Strategy 2: Prompt-Level Constraints.

Implements guardrails within LLM prompts to:
1. Define system instructions (persona, tone, JSON schema)
2. Add negative constraints (what NOT to do)
3. Filter off-topic content (topic-specific allowlist/blocklist)
4. Validate LLM input before sending
5. Validate and sanitize LLM output before storing

Security Focus: Prevents prompt injection and ensures output compliance.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

import anthropic

# Configure logging
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Claude, GPT, etc.)."""

    @abstractmethod
    def call_llm(
        self, system_prompt: str, user_message: str, temperature: float = 0.7
    ) -> str:
        """Call LLM and return response text."""
        pass


class ClaudeProvider(LLMProvider):
    """Claude API provider via Anthropic."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def call_llm(
        self, system_prompt: str, user_message: str, temperature: float = 0.7
    ) -> str:
        """
        Call Claude API.

        Args:
            system_prompt: System instructions for Claude
            user_message: User/content message
            temperature: Creativity parameter (0-1)

        Returns:
            Claude's response text
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return message.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}", exc_info=True)
            raise


class SystemPrompt:
    """Generates comprehensive system instructions for LLM."""

    @staticmethod
    def summarization_prompt() -> str:
        """System prompt for article summarization."""
        return """You are an expert AI analyst specializing in summarizing technical news articles.

**Persona:** Objective, professional, technically accurate analyst
**Tone:** Neutral, informative, no promotional language

**Task:** Summarize the provided AI/ML/tech article into a concise, actionable summary.

**Output Format:** Return ONLY valid JSON with this structure:
{
  "title": "Brief headline summarizing the key insight (max 10 words)",
  "summary": "2-3 sentence summary of the article (max 150 words)",
  "key_points": ["point 1", "point 2", "point 3"],
  "relevance_score": 0.0-1.0,
  "category": "one of: AI, ML, LLM, Computer Vision, NLP, Robotics, Other"
}

**Critical Constraints:**
- Do NOT mention source URLs, links, or "read more" calls
- Do NOT include promotional language, marketing claims, or advertisements
- Do NOT preserve author names or publication details
- Do NOT speculate beyond what's in the article
- Do NOT include HTML, Markdown, or escape sequences
- Return ONLY the JSON object, no additional text or explanation
- Ensure JSON is valid and parseable
- All string values must be plain text (no nested JSON)

**Content Focus:**
- Focus on: Machine Learning, LLMs, Generative AI, Deep Learning, NLP, Computer Vision, Robotics
- Ignore: Financial/stock news, Politics, Misinformation, Sports, Entertainment, Celebrity gossip

**Quality Standards:**
- Preserve technical accuracy
- Highlight novel contributions or insights
- Flag if article appears to be low-quality or spam (set relevance_score to 0.0)
"""

    @staticmethod
    def video_idea_prompt() -> str:
        """System prompt for video idea generation."""
        return """You are a creative video producer specializing in AI/ML educational content.

**Persona:** Creative but technical, educational focus, no hype
**Tone:** Engaging, informative, suitable for developer/researcher audience

**Task:** Generate compelling video content ideas based on summarized articles.

**Output Format:** Return ONLY valid JSON with this structure:
{
  "video_title": "Catchy but accurate title (max 60 characters)",
  "video_description": "2-3 sentence description of what the video covers (max 200 words)",
  "content_outline": [
    "Section 1: Introduction and problem statement",
    "Section 2: Technical deep-dive",
    "Section 3: Real-world applications",
    "Section 4: Conclusion and next steps"
  ],
  "target_duration_minutes": 5-15,
  "suggested_thumbnail_prompt": "Detailed description for image generation (max 100 words)",
  "difficulty_level": "Beginner/Intermediate/Advanced",
  "estimated_engagement_score": 0.0-1.0
}

**Critical Constraints:**
- Do NOT mention source URLs, original article references, or author names
- Do NOT use clickbait, sensationalism, or misleading titles
- Do NOT include promotional content or sponsored messaging
- Do NOT reference user data or personal information
- Do NOT include HTML, Markdown, or escape sequences
- Return ONLY the JSON object, no additional text or explanation
- Ensure JSON is valid and parseable
- All string values must be plain text

**Content Guidelines:**
- Create educational, reproducible content
- Include hands-on code examples or experiments where applicable
- Avoid overhyped trends; focus on substance
- Thumbnail suggestions should be clear and professional

**Quality Standards:**
- Content should be appropriate for technical YouTube audience
- Ensure ideas are unique and not saturated in the market
- Difficulty level should match target audience
"""

    @staticmethod
    def get_prompt(task: str) -> str:
        """
        Get system prompt for specified task.

        Args:
            task: "summarization" or "video_idea"

        Returns:
            System prompt text
        """
        if task == "summarization":
            return SystemPrompt.summarization_prompt()
        elif task == "video_idea":
            return SystemPrompt.video_idea_prompt()
        else:
            raise ValueError(f"Unknown task: {task}")


class InputValidator:
    """Validates input before sending to LLM."""

    # Suspicious patterns that indicate injection attempts
    INJECTION_PATTERNS = [
        r"\\x[0-9a-fA-F]{2}",  # Hex escape sequences
        r"\\u[0-9a-fA-F]{4}",  # Unicode escape sequences
        r"<script",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"SELECT\s+|INSERT\s+|UPDATE\s+|DELETE\s+",  # SQL keywords
        r"\$\{.*?\}",  # Template injection
        r"\{\{.*?\}\}",  # Template literals
        r"__proto__",  # Prototype pollution
        r"constructor\s*\[",  # Constructor access
    ]

    # Maximum allowed input length (tokens)
    MAX_INPUT_LENGTH = 8000

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

        # Check length (rough token estimate: 1 token ≈ 4 characters)
        if len(text) > InputValidator.MAX_INPUT_LENGTH * 4:
            reason = f"Input too long (>{InputValidator.MAX_INPUT_LENGTH} tokens)"
            return False, reason

        # Check for injection patterns
        for pattern in InputValidator.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = f"Detected suspicious pattern: {pattern}"
                logger.warning(f"Input validation failed: {reason}")
                if strict_mode:
                    return False, reason

        # Check for control characters
        if re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", text):
            reason = "Detected control characters"
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        # Check for excessive special characters
        special_chars = len(re.findall(r"[^\w\s\.\,\-\:\!\?\'\"\(\)\&\;\#\@]", text))
        special_ratio = special_chars / len(text) if text else 0
        if special_ratio > 0.20:  # More than 20% special chars
            reason = f"Excessive special characters ({special_ratio:.1%})"
            logger.warning(f"Input validation failed: {reason}")
            if strict_mode:
                return False, reason

        return True, None


class OutputValidator:
    """Validates and sanitizes LLM output."""

    @staticmethod
    def validate_json_schema(
        response: str, expected_keys: List[str]
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate that LLM response is valid JSON with expected keys.

        Args:
            response: LLM response text
            expected_keys: List of required keys in JSON

        Returns:
            Tuple of (is_valid, reason_if_invalid, parsed_json)
        """
        try:
            # Parse JSON
            data = json.loads(response)

            # Validate it's a dict
            if not isinstance(data, dict):
                return False, "Response is not a JSON object", None

            # Check for required keys
            missing_keys = [k for k in expected_keys if k not in data]
            if missing_keys:
                return False, f"Missing required keys: {missing_keys}", None

            # Check for null/empty values in required fields
            for key in expected_keys:
                value = data[key]
                if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                    return False, f"Required field '{key}' is empty", None

            # Check for injection patterns in string values
            for key, value in data.items():
                if isinstance(value, str):
                    is_clean = InputValidator.validate(value, strict_mode=False)
                    if not is_clean[0]:
                        logger.warning(f"Field '{key}' may contain suspicious content")

            return True, None, data

        except json.JSONDecodeError as e:
            reason = f"Invalid JSON in response: {str(e)}"
            logger.error(reason)
            return False, reason, None

    @staticmethod
    def sanitize_output(data: Dict[str, any]) -> Dict[str, any]:
        """
        Clean and sanitize LLM output dict.

        Args:
            data: Parsed JSON dict from LLM

        Returns:
            Sanitized dict
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Remove HTML/Markdown
                value = re.sub(r"<[^>]+>", "", value)
                value = re.sub(r"\*\*|__", "", value)
                # Normalize whitespace
                value = re.sub(r"\s+", " ", value).strip()
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = [
                    re.sub(r"\s+", " ", str(item)).strip() if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized


class TopicFilter:
    """Filters content by topic relevance."""

    # Allowlist: topics to focus on
    ALLOWLIST_TOPICS = {
        "machine learning",
        "artificial intelligence",
        "deep learning",
        "large language model",
        "llm",
        "neural network",
        "transformer",
        "nlp",
        "natural language processing",
        "computer vision",
        "robotics",
        "generative ai",
        "prompt engineering",
        "fine-tuning",
        "inference",
        "gpu",
        "distributed training",
        "model optimization",
        "ai safety",
        "alignment",
    }

    # Blocklist: topics to ignore
    BLOCKLIST_TOPICS = {
        "stock",
        "financial",
        "cryptocurrency",
        "crypto",
        "bitcoin",
        "nft",
        "politics",
        "election",
        "misinformation",
        "conspiracy",
        "sports",
        "entertainment",
        "celebrity",
        "gossip",
        "gaming",
        "mobile app",
        "real estate",
        "dating",
    }

    @staticmethod
    def is_topic_relevant(title: str, body: str) -> Tuple[bool, str]:
        """
        Check if content matches allowlist/blocklist criteria.

        Args:
            title: Article title
            body: Article body text

        Returns:
            Tuple of (is_relevant, reason)
        """
        combined_text = (title + " " + body).lower()

        # Check blocklist first (higher priority)
        for blocked_topic in TopicFilter.BLOCKLIST_TOPICS:
            if blocked_topic in combined_text:
                return False, f"Blocklisted topic: {blocked_topic}"

        # Check allowlist (must match at least one)
        matched_topics = []
        for allowed_topic in TopicFilter.ALLOWLIST_TOPICS:
            if allowed_topic in combined_text:
                matched_topics.append(allowed_topic)

        if matched_topics:
            return True, f"Matched topics: {', '.join(matched_topics[:3])}"
        else:
            return False, "No relevant topics found in allowlist"


class GuardrailsManager:
    """Orchestrates full guardrails pipeline."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize guardrails manager.

        Args:
            llm_provider: LLM provider instance (defaults to Claude)
        """
        self.llm = llm_provider or ClaudeProvider()
        self.input_validator = InputValidator()
        self.output_validator = OutputValidator()
        self.topic_filter = TopicFilter()

    def summarize_article(self, title: str, body: str) -> Optional[Dict]:
        """
        Summarize article with full guardrails.

        Args:
            title: Article title
            body: Article body

        Returns:
            Summarized article dict, or None if validation failed
        """
        logger.info(f"Summarizing: {title[:50]}...")

        # Step 1: Topic filter
        is_relevant, reason = self.topic_filter.is_topic_relevant(title, body)
        if not is_relevant:
            logger.warning(f"Article off-topic: {reason}")
            return None

        # Step 2: Input validation
        combined = f"{title}\n\n{body}"
        is_valid, reason = self.input_validator.validate(combined, strict_mode=True)
        if not is_valid:
            logger.warning(f"Input validation failed: {reason}")
            return None

        # Step 3: Call LLM
        try:
            system_prompt = SystemPrompt.get_prompt("summarization")
            response = self.llm.call_llm(system_prompt, combined)
            logger.debug(f"LLM response: {response[:200]}...")
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return None

        # Step 4: Output validation
        expected_keys = ["title", "summary", "key_points", "relevance_score", "category"]
        is_valid, reason, data = self.output_validator.validate_json_schema(
            response, expected_keys
        )
        if not is_valid:
            logger.error(f"Output validation failed: {reason}")
            return None

        # Step 5: Sanitize output
        sanitized = self.output_validator.sanitize_output(data)
        logger.info(f"Successfully summarized: {sanitized['title']}")
        return sanitized

    def generate_video_idea(self, summary: Dict) -> Optional[Dict]:
        """
        Generate video idea from summary with full guardrails.

        Args:
            summary: Summarized article dict (from summarize_article)

        Returns:
            Video idea dict, or None if validation failed
        """
        logger.info(f"Generating video idea for: {summary['title']}")

        # Step 1: Filter by relevance score
        if summary.get("relevance_score", 0) < 0.5:
            logger.warning(f"Summary has low relevance score: {summary['relevance_score']}")
            return None

        # Step 2: Input validation
        summary_text = json.dumps(summary)
        is_valid, reason = self.input_validator.validate(summary_text, strict_mode=True)
        if not is_valid:
            logger.warning(f"Input validation failed: {reason}")
            return None

        # Step 3: Call LLM
        try:
            system_prompt = SystemPrompt.get_prompt("video_idea")
            response = self.llm.call_llm(system_prompt, summary_text, temperature=0.8)
            logger.debug(f"LLM response: {response[:200]}...")
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return None

        # Step 4: Output validation
        expected_keys = [
            "video_title",
            "video_description",
            "content_outline",
            "target_duration_minutes",
            "suggested_thumbnail_prompt",
            "difficulty_level",
            "estimated_engagement_score",
        ]
        is_valid, reason, data = self.output_validator.validate_json_schema(
            response, expected_keys
        )
        if not is_valid:
            logger.error(f"Output validation failed: {reason}")
            return None

        # Step 5: Sanitize output
        sanitized = self.output_validator.sanitize_output(data)
        logger.info(f"Successfully generated video idea: {sanitized['video_title']}")
        return sanitized

    def batch_process(
        self, articles: List[Dict[str, str]], task: str = "summarization"
    ) -> List[Dict]:
        """
        Process batch of articles with guardrails.

        Args:
            articles: List of article dicts with 'title' and 'body' keys
            task: "summarization" or "video_idea"

        Returns:
            List of processed articles (failed items filtered out)
        """
        results = []

        for i, article in enumerate(articles):
            try:
                if task == "summarization":
                    result = self.summarize_article(
                        article.get("title", ""), article.get("body", "")
                    )
                elif task == "video_idea":
                    result = self.generate_video_idea(article)
                else:
                    logger.warning(f"Unknown task: {task}")
                    continue

                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error processing article {i}: {str(e)}", exc_info=True)
                continue

        logger.info(
            f"Processed {len(results)} out of {len(articles)} articles "
            f"({100 * len(results) / len(articles):.1f}% pass rate)"
        )

        return results
