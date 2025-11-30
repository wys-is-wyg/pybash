"""
Configuration settings for AI News Tracker application.

This module contains all configuration constants, API endpoints,
file paths, and processing parameters used throughout the application.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application configuration class."""
    
    # Leonardo AI API Configuration
    LEONARDO_API_KEY: str = os.getenv("LEONARDO_API_KEY", "")
    LEONARDO_API_BASE_URL: str = "https://cloud.leonardo.ai/api/rest/v1"
    LEONARDO_DEFAULT_MODEL_ID: str = "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3"  # Leonardo Diffusion XL
    LEONARDO_THUMBNAIL_WIDTH: int = 512
    LEONARDO_THUMBNAIL_HEIGHT: int = 512
    LEONARDO_GENERATION_TIMEOUT: int = 300  # seconds
    LEONARDO_POLL_INTERVAL: int = 5  # seconds between status checks
    
    # RSS Feed URLs to scrape
    RSS_FEED_URLS: List[str] = [
        "https://feeds.feedburner.com/oreilly/radar",  # O'Reilly Radar
        "https://www.theverge.com/rss/index.xml",  # The Verge
        "https://techcrunch.com/feed/",  # TechCrunch
        "https://www.wired.com/feed/rss",  # Wired
        "https://rss.cnn.com/rss/edition.rss",  # CNN Tech
    ]
    
    # Social Media Configuration (for future implementation)
    TWITTER_HASHTAGS: List[str] = [
        "#AI",
        "#MachineLearning",
        "#ArtificialIntelligence",
        "#DeepLearning",
    ]
    
    # File Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    APP_DIR: Path = BASE_DIR / "app"
    DATA_DIR: Path = APP_DIR / "data"
    LOGS_DIR: Path = APP_DIR / "logs"
    
    # Data File Names
    RAW_NEWS_FILE: str = "raw_news.json"
    SUMMARIES_FILE: str = "summaries.json"
    VIDEO_IDEAS_FILE: str = "video_ideas.json"
    THUMBNAILS_FILE: str = "thumbnails.json"
    FEED_FILE: str = "feed.json"
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    
    # Batch Processing Parameters
    BATCH_SIZE: int = 10  # Process items in batches
    MAX_RETRIES: int = 3  # Maximum retry attempts for API calls
    RETRY_DELAY: int = 2  # Seconds to wait between retries
    
    # Summarization Configuration
    SUMMARY_MAX_WORDS: int = 150
    SUMMARY_MIN_WORDS: int = 50
    
    # Video Idea Generation Configuration
    MAX_VIDEO_IDEAS_PER_ARTICLE: int = 3
    
    # API Server Configuration
    PYTHON_APP_PORT: int = int(os.getenv("PYTHON_APP_PORT", "5001"))
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))
    N8N_PORT: int = int(os.getenv("N8N_PORT", "5678"))
    
    # n8n Configuration
    N8N_API_KEY: str = os.getenv("N8N_API_KEY", "")
    N8N_AUTH_PASSWORD: str = os.getenv("N8N_AUTH_PASSWORD", "")
    N8N_BASE_URL: str = f"http://n8n:{N8N_PORT}"
    
    @classmethod
    def get_data_file_path(cls, filename: str) -> Path:
        """Get full path to a data file."""
        return cls.DATA_DIR / filename
    
    @classmethod
    def get_log_file_path(cls, filename: str) -> Path:
        """Get full path to a log file."""
        return cls.LOGS_DIR / filename
    
    @classmethod
    def ensure_directories_exist(cls) -> None:
        """Ensure all required directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Create singleton instance
settings = Settings()

