"""
RSS feed scraper for AI News Tracker.

Fetches and parses RSS feeds from multiple sources to collect AI news articles.
"""

import feedparser
import requests
import re
import html
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from app.config import settings
from app.scripts.data_manager import save_json


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
    
    feeds = []
    
    for url in feed_urls:
        try:
            # Set a reasonable timeout
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'AI News Tracker/1.0'
            })
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            feeds.append(feed)
            
        except requests.RequestException:
            continue
        except Exception:
            continue
    return feeds


def extract_text_from_html(html_content: str) -> str:
    """
    Extract only text content from HTML, removing all tags (including code, img, a, etc.).
    
    Args:
        html_content: HTML string that may contain tags
        
    Returns:
        Clean text content without any HTML tags
    """
    if not html_content:
        return ''
    
    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements completely
        for script in soup(["script", "style", "code", "pre"]):
            script.decompose()
        
        # Get text content (this automatically removes all tags)
        text = soup.get_text(separator=' ', strip=True)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception:
        # Fallback to regex-based cleaning if BeautifulSoup fails
        # Remove HTML tags using regex
        text = re.sub(r'<[^>]+>', '', html_content)
        # Decode HTML entities
        text = html.unescape(text)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text


def parse_feed_entries(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Parse feedparser entries into structured news items.
    
    Args:
        entries: List of feedparser entry objects
        
    Returns:
        List of structured news item dictionaries
    """
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
                # Keep \n, \r, \t, but remove other control chars (0x00-0x1F except 0x09, 0x0A, 0x0D)
                return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', str(text))
            
            # Extract summary and clean HTML tags
            raw_summary = getattr(entry, 'summary', '')
            cleaned_summary = extract_text_from_html(raw_summary) if raw_summary else ''
            
            news_item = {
                'title': clean_text(getattr(entry, 'title', '')),
                'summary': clean_text(cleaned_summary),
                'source': clean_text(getattr(entry, 'source', {}).get('title', '') if hasattr(entry, 'source') else ''),
                'source_url': getattr(entry, 'link', ''),
                'published_date': published_date,
                'author': clean_text(getattr(entry, 'author', '')),
                'tags': [],  # RSS tags not used - only visual tags from categorization
            }
            
            news_items.append(news_item)
            
        except Exception:
            continue
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


def main():
    """Main execution function for command-line invocation."""
    try:
        # Fetch feeds
        feeds = fetch_rss_feeds()
        
        # Collect all entries
        all_entries = []
        for feed in feeds:
            all_entries.extend(feed.entries)
        
        # Parse entries
        news_items = parse_feed_entries(all_entries)
        
        # Save to file
        save_raw_news(news_items)
        
        return 0
        
    except Exception:
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    # Initialize error logging for this script
    from app.scripts.error_logger import initialize_error_logging
    initialize_error_logging()
    
    exit_code = main()
    sys.exit(exit_code)

