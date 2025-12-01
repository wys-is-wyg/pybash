"""
Feed Sources Configuration for AI News Tracker.

Defines data feed sources (Google News, Reddit, Twitter/X) with API endpoints,
authentication requirements, feed-specific parameters, and guardrail constraints.

SECURITY NOTE: All API keys must be stored in .env file, never hardcoded.
"""

import os
import logging
from typing import Dict, List, Optional, Set, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class FeedConfig:
    """Base configuration class for feed sources."""

    def __init__(self, name: str, feed_type: str):
        self.name = name
        self.feed_type = feed_type
        self.enabled = True
        self.rate_limit_per_minute = 60
        self.timeout_seconds = 30


class GoogleNewsFeed(FeedConfig):
    """
    Google News API Configuration.
    
    Feed A: Real-time news articles on AI and technology topics.
    
    Setup Instructions:
    1. Visit: https://newsapi.org/
    2. Sign up and get API key
    3. Store in .env as: GOOGLE_NEWS_API_KEY=your_key_here
    
    Query Parameters:
    - Query terms: "artificial intelligence", "machine learning", "deep learning", "LLM"
    - Sort by: publishedAt (most recent first)
    - Language: en
    - Max articles per request: 100
    """

    def __init__(self):
        super().__init__(name="Google News", feed_type="REST_API")
        self.api_key = os.getenv("GOOGLE_NEWS_API_KEY", "")
        self.base_url = "https://newsapi.org/v2/everything"
        self.query_terms = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "large language models",
            "LLM",
            "generative AI",
        ]
        self.sort_by = "publishedAt"
        self.language = "en"
        self.page_size = 100
        self.rate_limit_per_minute = 40  # NewsAPI free tier: 40 requests/day
        
        # Validation
        if not self.api_key:
            raise ValueError(
                "GOOGLE_NEWS_API_KEY not found in .env. "
                "Visit https://newsapi.org/ to get your API key."
            )

    def get_endpoint(self) -> str:
        """Return the API endpoint for Google News."""
        return self.base_url

    def get_headers(self) -> Dict[str, str]:
        """Return HTTP headers for requests."""
        return {
            "User-Agent": "AI-News-Tracker/1.0",
            "Authorization": f"Bearer {self.api_key}",
        }

    def get_params(self, query: str, page: int = 1) -> Dict[str, str]:
        """Return query parameters for the API request."""
        return {
            "q": query,
            "sortBy": self.sort_by,
            "language": self.language,
            "pageSize": str(self.page_size),
            "page": str(page),
        }


class RedditFeed(FeedConfig):
    """
    Reddit API Configuration.
    
    Feed B: Community discussions on machine learning and AI trends.
    
    Setup Instructions:
    1. Visit: https://www.reddit.com/prefs/apps
    2. Create a "script" application
    3. Get: client_id, client_secret, user_agent
    4. Store in .env as:
       - REDDIT_CLIENT_ID=your_id_here
       - REDDIT_CLIENT_SECRET=your_secret_here
       - REDDIT_USER_AGENT=AI-News-Tracker/1.0 by YourUsername
    
    Subreddits:
    - r/MachineLearning: Research and papers
    - r/artificial: General AI discussions
    - r/LanguageModels: LLM-specific discussions
    """

    def __init__(self):
        super().__init__(name="Reddit", feed_type="REST_API")
        self.client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.user_agent = os.getenv(
            "REDDIT_USER_AGENT", "AI-News-Tracker/1.0 (by Anonymous)"
        )
        
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1/access_token"
        
        self.subreddits = [
            "MachineLearning",
            "artificial",
            "LanguageModels",
            "OpenAI",
            "LocalLLaMA",
        ]
        
        self.sort_by = "hot"  # hot, new, top
        self.time_filter = "day"  # hour, day, week, month, year
        self.limit = 50  # Posts per subreddit
        self.rate_limit_per_minute = 60  # Reddit allows ~60 requests/min
        
        # Validation
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not found in .env. "
                "Visit https://www.reddit.com/prefs/apps to register your app."
            )

    def get_auth_url(self) -> str:
        """Return the OAuth authentication endpoint."""
        return self.auth_url

    def get_headers(self) -> Dict[str, str]:
        """Return HTTP headers for requests."""
        return {
            "User-Agent": self.user_agent,
        }

    def get_credentials(self) -> tuple:
        """Return (client_id, client_secret) for OAuth authentication."""
        return (self.client_id, self.client_secret)

    def get_subreddit_endpoint(self, subreddit: str) -> str:
        """Return the API endpoint for a specific subreddit."""
        return f"{self.base_url}/r/{subreddit}/{self.sort_by}"

    def get_params(self, limit: int = None) -> Dict[str, str]:
        """Return query parameters for subreddit requests."""
        return {
            "limit": str(limit or self.limit),
            "t": self.time_filter,
        }


class TwitterFeed(FeedConfig):
    """
    Twitter/X API Configuration.
    
    Feed C: Expert analysis and opinions from key AI researchers and practitioners.
    
    Setup Instructions:
    1. Visit: https://developer.twitter.com/en/portal/dashboard
    2. Create a project and app
    3. Get: Bearer Token (API v2)
    4. Store in .env as: TWITTER_BEARER_TOKEN=your_token_here
    
    Key Accounts to Follow:
    - @ylecun (Yann LeCun, Meta AI)
    - @karpathy (Andrej Karpathy)
    - @hardmaru (David Ha)
    - @emollick (Ethan Mollick)
    - @jacksonphillips (Jackson Phillips)
    - OpenAI, Anthropic, DeepMind accounts
    """

    def __init__(self):
        super().__init__(name="Twitter/X", feed_type="REST_API")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "")
        
        self.base_url = "https://api.twitter.com/2"
        self.search_endpoint = f"{self.base_url}/tweets/search/recent"
        
        # Key accounts and hashtags to monitor
        self.key_accounts = [
            "ylecun",
            "karpathy",
            "hardmaru",
            "emollick",
            "jacksonphillips",
        ]
        
        self.hashtags = [
            "#AI",
            "#MachineLearning",
            "#LLM",
            "#GenerativeAI",
            "#ArtificialIntelligence",
            "#DeepLearning",
        ]
        
        self.max_results = 100  # Per request
        self.rate_limit_per_minute = 300  # API v2 free tier
        self.timeout_seconds = 15
        
        # Validation
        if not self.bearer_token:
            raise ValueError(
                "TWITTER_BEARER_TOKEN not found in .env. "
                "Visit https://developer.twitter.com to get your Bearer Token."
            )

    def get_headers(self) -> Dict[str, str]:
        """Return HTTP headers for requests."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "AI-News-Tracker/1.0",
        }

    def get_search_endpoint(self) -> str:
        """Return the search endpoint."""
        return self.search_endpoint

    def get_params(self, query: str, max_results: int = None) -> Dict[str, str]:
        """Return query parameters for tweet search."""
        return {
            "query": query,
            "max_results": str(max_results or self.max_results),
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "expansions": "author_id",
            "user.fields": "name,username,verified",
        }


class FeedSourcesManager:
    """Manager for all feed sources."""

    def __init__(self):
        """Initialize all feed sources."""
        self.feeds: Dict[str, FeedConfig] = {}
        
        try:
            self.feeds["google_news"] = GoogleNewsFeed()
        except ValueError as e:
            print(f"⚠️  Google News Feed disabled: {e}")
        
        try:
            self.feeds["reddit"] = RedditFeed()
        except ValueError as e:
            print(f"⚠️  Reddit Feed disabled: {e}")
        
        try:
            self.feeds["twitter"] = TwitterFeed()
        except ValueError as e:
            print(f"⚠️  Twitter/X Feed disabled: {e}")

    def get_enabled_feeds(self) -> Dict[str, FeedConfig]:
        """Return only enabled feed sources."""
        return {k: v for k, v in self.feeds.items() if v.enabled}

    def get_feed(self, feed_name: str) -> Optional[FeedConfig]:
        """Get a specific feed by name."""
        return self.feeds.get(feed_name)

    def list_feeds(self) -> List[str]:
        """List all configured feed names."""
        return list(self.feeds.keys())


# ============================================================================
# Guardrail Constraints - Strategy 2 Configuration
# ============================================================================


class GuardrailConstraints:
    """
    Guardrail constraints for content filtering and validation.
    
    Applied per-feed and globally to ensure high-quality, on-topic content
    reaches the LLM for summarization and video idea generation.
    """

    def __init__(
        self,
        feed_name: str,
        min_relevance_score: float = 0.0,
        max_token_limit: int = 2000,
        enforce_topic_filter: bool = True,
        require_english: bool = True,
    ):
        """
        Initialize guardrail constraints.

        Args:
            feed_name: Name of the feed these constraints apply to
            min_relevance_score: Minimum relevance score (0.0-1.0) to accept content
            max_token_limit: Maximum tokens for truncation
            enforce_topic_filter: If True, apply topic allowlist/blocklist
            require_english: If True, reject non-English content
        """
        self.feed_name = feed_name
        self.min_relevance_score = min_relevance_score
        self.max_token_limit = max_token_limit
        self.enforce_topic_filter = enforce_topic_filter
        self.require_english = require_english

    def __repr__(self) -> str:
        return (
            f"GuardrailConstraints(feed={self.feed_name}, "
            f"min_score={self.min_relevance_score}, "
            f"max_tokens={self.max_token_limit}, "
            f"enforce_filter={self.enforce_topic_filter})"
        )


class AllowlistBlocklist:
    """
    Domain and source filtering for feed content.
    
    Maintains allowlists of trusted domains and blocklists of suspicious sources.
    """

    def __init__(self):
        """Initialize domain allowlist and blocklist."""
        # Safe, trusted domains for each feed
        self.domain_allowlist = {
            "google_news": {
                "newsapi.org",
                "bbc.com",
                "techcrunch.com",
                "theverge.com",
                "wired.com",
                "arstechnica.com",
                "medium.com",
                "github.com",
                "arxiv.org",
                "nature.com",
                "science.org",
                "openai.com",
                "deepmind.com",
                "anthropic.com",
                "meta.com",
                "nvidia.com",
                "ieee.org",
                "acm.org",
                "springer.com",
            },
            "reddit": {
                "reddit.com",
                "v.redd.it",  # Reddit video
                "reddit.com/r/MachineLearning",
                "reddit.com/r/artificial",
                "reddit.com/r/LanguageModels",
                "reddit.com/r/OpenAI",
                "reddit.com/r/LocalLLaMA",
            },
            "twitter": {
                "twitter.com",
                "x.com",
                "t.co",  # Twitter URL shortener
            },
        }

        # Domains to explicitly block (spam, misinformation, low-quality)
        self.domain_blocklist = {
            "en.wikipedia.org",  # Too general, not original research
            "reddit.com/r/conspiracy",
            "reddit.com/r/politics",
            "reddit.com/r/finance",  # Financial content not relevant
            "reddit.com/r/stocks",
            "medium.com/cryptocurrency",
            "medium.com/crypto",
            "clickbait-domain.com",  # Placeholder for known spam sites
        }

    def is_domain_safe(self, url: str, feed_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if domain is in allowlist for specific feed.

        Args:
            url: Source URL to validate
            feed_name: Feed name (google_news, reddit, twitter)

        Returns:
            Tuple of (is_safe, reason_if_not_safe)
        """
        if not url:
            return False, "No URL provided"

        url_lower = url.lower()

        # Check blocklist first (higher priority)
        for blocked in self.domain_blocklist:
            if blocked in url_lower:
                return False, f"Domain in blocklist: {blocked}"

        # Get allowlist for this feed
        feed_allowlist = self.domain_allowlist.get(feed_name, set())

        if not feed_allowlist:
            logger.warning(f"No allowlist defined for feed: {feed_name}")
            return False, f"No allowlist configured for feed: {feed_name}"

        # Check allowlist
        for allowed in feed_allowlist:
            if allowed in url_lower:
                return True, None

        # Domain not in allowlist
        return False, f"Domain not in allowlist for {feed_name}"

    def add_domain_to_allowlist(self, feed_name: str, domain: str) -> None:
        """Add domain to allowlist for a feed."""
        if feed_name not in self.domain_allowlist:
            self.domain_allowlist[feed_name] = set()
        self.domain_allowlist[feed_name].add(domain)
        logger.info(f"Added {domain} to allowlist for {feed_name}")

    def add_domain_to_blocklist(self, domain: str) -> None:
        """Add domain to global blocklist."""
        self.domain_blocklist.add(domain)
        logger.info(f"Added {domain} to global blocklist")

    def get_feed_allowlist(self, feed_name: str) -> Set[str]:
        """Get allowlist for a specific feed."""
        return self.domain_allowlist.get(feed_name, set())


class TopicAllowlistBlocklist:
    """
    Topic-based content filtering (mirrors guardrails.py TopicFilter).
    
    Ensures content matches AI/ML topics before LLM processing.
    """

    def __init__(self):
        """Initialize topic allowlist and blocklist."""
        self.topic_allowlist = {
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
            "foundation model",
            "multimodal",
            "embedding",
            "vector database",
            "rag",
            "retrieval augmented",
        }

        self.topic_blocklist = {
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
            "fashion",
            "health",
            "medical",
            "weather",
        }

    def is_topic_relevant(self, title: str, body: str) -> Tuple[bool, Optional[str]]:
        """
        Check if content is topically relevant.

        Args:
            title: Article title
            body: Article body

        Returns:
            Tuple of (is_relevant, reason_if_not)
        """
        combined_text = (title + " " + body).lower()

        # Check blocklist first
        for blocked in self.topic_blocklist:
            if blocked in combined_text:
                return False, f"Blocklisted topic: {blocked}"

        # Check allowlist
        matched = [t for t in self.topic_allowlist if t in combined_text]
        if matched:
            return True, f"Matched topics: {', '.join(matched[:3])}"

        return False, "No relevant topics found"

    def add_allowed_topic(self, topic: str) -> None:
        """Add topic to allowlist."""
        self.topic_allowlist.add(topic.lower())
        logger.info(f"Added '{topic}' to topic allowlist")

    def add_blocked_topic(self, topic: str) -> None:
        """Add topic to blocklist."""
        self.topic_blocklist.add(topic.lower())
        logger.info(f"Added '{topic}' to topic blocklist")


class FeedGuardrailsConfig:
    """
    Central configuration for feed guardrails.
    
    Orchestrates domain filtering, topic filtering, and constraint application.
    """

    def __init__(self):
        """Initialize guardrail configuration."""
        # Per-feed guardrail constraints
        self.constraints = {
            "google_news": GuardrailConstraints(
                feed_name="google_news",
                min_relevance_score=0.6,
                max_token_limit=2000,
                enforce_topic_filter=True,
            ),
            "reddit": GuardrailConstraints(
                feed_name="reddit",
                min_relevance_score=0.5,  # Lower threshold for community content
                max_token_limit=2000,
                enforce_topic_filter=True,
            ),
            "twitter": GuardrailConstraints(
                feed_name="twitter",
                min_relevance_score=0.7,  # Higher threshold for tweets (can be brief)
                max_token_limit=1000,
                enforce_topic_filter=True,
            ),
        }

        # Domain filtering
        self.domain_filter = AllowlistBlocklist()

        # Topic filtering
        self.topic_filter = TopicAllowlistBlocklist()

    def validate_content(
        self, feed_name: str, title: str, body: str, source_url: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate content against all guardrails.

        Args:
            feed_name: Feed source name
            title: Article title
            body: Article body
            source_url: Source URL

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Step 1: Domain validation
        is_safe, reason = self.domain_filter.is_domain_safe(source_url, feed_name)
        if not is_safe:
            logger.warning(f"Domain validation failed: {reason}")
            return False, reason

        # Step 2: Topic validation
        constraints = self.constraints.get(feed_name)
        if constraints and constraints.enforce_topic_filter:
            is_relevant, reason = self.topic_filter.is_topic_relevant(title, body)
            if not is_relevant:
                logger.warning(f"Topic validation failed: {reason}")
                return False, reason

        logger.info(f"Content validated for {feed_name}: {title[:50]}...")
        return True, None

    def get_constraints(self, feed_name: str) -> Optional[GuardrailConstraints]:
        """Get guardrail constraints for a feed."""
        return self.constraints.get(feed_name)

    def update_constraints(self, feed_name: str, **kwargs) -> None:
        """Update constraints for a feed."""
        if feed_name in self.constraints:
            for key, value in kwargs.items():
                if hasattr(self.constraints[feed_name], key):
                    setattr(self.constraints[feed_name], key, value)
                    logger.info(f"Updated {feed_name}.{key} = {value}")


# Global singleton instance
_guardrails_config = None


def get_guardrails_config() -> FeedGuardrailsConfig:
    """Get or create global guardrails configuration singleton."""
    global _guardrails_config
    if _guardrails_config is None:
        _guardrails_config = FeedGuardrailsConfig()
    return _guardrails_config

# Singleton instance
feed_manager = FeedSourcesManager()
