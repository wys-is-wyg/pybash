"""
RSS feed scraper for AI News Tracker.

Fetches and parses RSS feeds from multiple sources to collect AI news articles.
"""

import feedparser
import requests
from typing import List, Dict, Any
from datetime import datetime
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import save_json

logger = setup_logger(__name__)


def fetch_rss_feeds(feed_urls: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch RSS feeds from multiple URLs.
    
    Args:
        feed_urls: List of RSS feed URLs to fetch. If None, uses settings.RSS_FEED_URLS
        
    Returns:
        List of feedparser feed objects
    """
    if feed_urls is None:
        feed_urls = settings.RSS_FEED_URLS
    
    logger.info(f"Fetching {len(feed_urls)} RSS feeds")
    feeds = []
    
    for url in feed_urls:
        try:
            logger.debug(f"Fetching feed: {url}")
            # Set a reasonable timeout
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'AI News Tracker/1.0'
            })
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {url}: {feed.bozo_exception}")
            
            feeds.append(feed)
            logger.info(f"Successfully fetched feed: {url} ({len(feed.entries)} entries)")
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch feed {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error fetching feed {url}: {e}")
            continue
    
    logger.info(f"Fetched {len(feeds)} feeds successfully")
    return feeds


def parse_feed_entries(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Parse feedparser entries into structured news items.
    
    Args:
        entries: List of feedparser entry objects
        
    Returns:
        List of structured news item dictionaries
    """
    logger.info(f"Parsing {len(entries)} feed entries")
    news_items = []
    
    for entry in entries:
        try:
            # Extract published date
            published_date = ''
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_date = datetime(*entry.published_parsed[:6]).isoformat()
                except (ValueError, TypeError):
                    pass
            
            # Fallback to updated date if published not available
            if not published_date and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    published_date = datetime(*entry.updated_parsed[:6]).isoformat()
                except (ValueError, TypeError):
                    pass
            
            # Clean text fields to remove control characters that break JSON
            def clean_text(text):
                if not text:
                    return ''
                # Remove control characters except newlines, tabs, and carriage returns
                import re
                # Keep \n, \r, \t, but remove other control chars (0x00-0x1F except 0x09, 0x0A, 0x0D)
                return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', str(text))
            
            news_item = {
                'title': clean_text(getattr(entry, 'title', '')),
                'summary': clean_text(getattr(entry, 'summary', '')),
                'source': clean_text(getattr(entry, 'source', {}).get('title', '') if hasattr(entry, 'source') else ''),
                'source_url': getattr(entry, 'link', ''),
                'published_date': published_date,
                'author': clean_text(getattr(entry, 'author', '')),
                'tags': [clean_text(tag.term) for tag in getattr(entry, 'tags', [])],
            }
            
            news_items.append(news_item)
            
        except Exception as e:
            logger.warning(f"Failed to parse entry: {e}")
            continue
    
    logger.info(f"Successfully parsed {len(news_items)} news items")
    return news_items


def save_raw_news(news_items: List[Dict[str, Any]], output_file: str = None) -> None:
    """
    Save raw news items to JSON file.
    
    Args:
        news_items: List of news item dictionaries
        output_file: Output file path (defaults to settings.RAW_NEWS_FILE)
    """
    if output_file is None:
        output_file = settings.RAW_NEWS_FILE
    
    data = {
        'scraped_at': datetime.utcnow().isoformat(),
        'total_items': len(news_items),
        'items': news_items,
    }
    
    save_json(data, output_file)
    logger.info(f"Saved {len(news_items)} news items to {output_file}")


def main():
    """Main execution function for command-line invocation."""
    try:
        logger.info("Starting RSS scraping process")
        
        # Fetch feeds
        feeds = fetch_rss_feeds()
        
        # Collect all entries
        all_entries = []
        for feed in feeds:
            all_entries.extend(feed.entries)
        
        logger.info(f"Collected {len(all_entries)} total entries from all feeds")
        
        # Parse entries
        news_items = parse_feed_entries(all_entries)
        
        # Save to file
        save_raw_news(news_items)
        
        logger.info("RSS scraping completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"RSS scraping failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)

