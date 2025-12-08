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
    # Model IDs - Update these with actual model IDs from Leonardo API
    # Get model IDs from: https://docs.leonardo.ai/reference/getmodels or check your Leonardo dashboard
    LEONARDO_PHOTOREAL_MODEL_ID: str = os.getenv("LEONARDO_PHOTOREAL_MODEL_ID", "e316348f-7773-490e-adcd-46757e738c7e")  # Leonardo Photoreal
    LEONARDO_FLUXDEV_MODEL_ID: str = os.getenv("LEONARDO_FLUXDEV_MODEL_ID", "5c232a02-8c3a-47c6-9c7e-2b5e7b5b5b5b")  # Flux Dev (update with actual ID from API)
    LEONARDO_DEFAULT_MODEL_ID: str = LEONARDO_PHOTOREAL_MODEL_ID  # Default to Photoreal
    # Video thumbnail dimensions (4:3 aspect ratio)
    LEONARDO_THUMBNAIL_WIDTH: int = 1024  # 4:3 ratio
    LEONARDO_THUMBNAIL_HEIGHT: int = 768   # 4:3 ratio
    # Quality settings
    LEONARDO_USE_ALCHEMY: bool = True  # Enable Alchemy for better quality
    LEONARDO_PHOTOREAL_STRENGTH: float = 0.5  # 0.0 to 1.0, controls photorealism
    LEONARDO_PRESET_STYLE: str = "CINEMATIC"  # Options: CINEMATIC, ANIME, CREATIVE, DYNAMIC, ENVIRONMENT, GENERAL, ILLUSTRATION, PHOTOGRAPHY, RAYTRACED, RENDER_3D, SKETCH_BW, SKETCH_COLOR
    LEONARDO_ENHANCE_PROMPT: bool = True  # Enable prompt enhancement
    LEONARDO_GENERATION_TIMEOUT: int = 300  # seconds
    LEONARDO_POLL_INTERVAL: int = 5  # seconds between status checks
    
    # RSS Feed URLs to scrape
    RSS_FEED_URLS: List[str] = [
        # AI/ML focused feeds
        "https://feeds.feedburner.com/oreilly/radar",  # O'Reilly Radar
        "https://www.theverge.com/rss/index.xml",  # The Verge
        "https://techcrunch.com/feed/",  # TechCrunch
        "https://www.wired.com/feed/rss",  # Wired
        "https://arstechnica.com/feed/",  # Ars Technica
        "https://feeds.feedburner.com/venturebeat/SGBF",  # VentureBeat
        "https://www.artificialintelligence-news.com/feed/",  # AI News
        "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",  # ZDNet AI
        "https://www.analyticsvidhya.com/feed/",  # Analytics Vidhya
        "https://machinelearningmastery.com/feed/",  # Machine Learning Mastery
        "https://www.kdnuggets.com/feed",  # KDnuggets
        "https://towardsdatascience.com/feed",  # Towards Data Science
        "https://www.technologyreview.com/feed/",  # MIT Technology Review
        "https://www.quantamagazine.org/feed/",  # Quanta Magazine
        "https://spectrum.ieee.org/rss",  # IEEE Spectrum
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
    
    # Google AI Studio (Gemini) Configuration
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")
    GOOGLE_AI_MODEL: str = os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash")  # Fast model for video ideas
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "mailhog")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "kiwifruitpeter@gmail.com")
    
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

