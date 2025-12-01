"""
Feed Sources Configuration for AI News Tracker.

Defines data feed sources (Google News, Reddit, Twitter/X) with API endpoints,
authentication requirements, and feed-specific parameters.

SECURITY NOTE: All API keys must be stored in .env file, never hardcoded.
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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


# Singleton instance
feed_manager = FeedSourcesManager()
