"""
Data management utilities for AI News Tracker.

Handles JSON file operations and data merging for the pipeline.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import settings
from app.scripts.logger import setup_logger

logger = setup_logger(__name__)


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to JSON file (relative to data directory or absolute)
        
    Returns:
        Dictionary containing parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(file_path)
    
    # If relative path, assume it's in data directory
    if not path.is_absolute():
        path = settings.get_data_file_path(file_path)
    
    logger.debug(f"Loading JSON from: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded JSON from {path}")
        return data
    except FileNotFoundError:
        logger.warning(f"File not found: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        raise


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Dictionary to save as JSON
        file_path: Path to JSON file (relative to data directory or absolute)
        
    Raises:
        OSError: If file cannot be written
    """
    path = Path(file_path)
    
    # If relative path, assume it's in data directory
    if not path.is_absolute():
        path = settings.get_data_file_path(file_path)
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.debug(f"Saving JSON to: {path}")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved JSON to {path}")
    except OSError as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        raise


def merge_feeds(
    news_items: List[Dict[str, Any]],
    video_ideas: List[Dict[str, Any]],
    thumbnails: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge news items, video ideas, and thumbnails into unified feed structure.
    
    Args:
        news_items: List of news article dictionaries
        video_ideas: List of video idea dictionaries
        thumbnails: List of thumbnail dictionaries with image paths
        
    Returns:
        List of merged feed items with unified structure
    """
    logger.info(f"Merging {len(news_items)} news items, {len(video_ideas)} video ideas, {len(thumbnails)} thumbnails")
    
    # Create thumbnail lookup by video idea ID or title
    thumbnail_lookup = {}
    for thumb in thumbnails:
        # Match thumbnails to video ideas by ID, title, or source
        key = thumb.get('video_idea_id') or thumb.get('title') or thumb.get('source', '')
        if key:
            thumbnail_lookup[key] = thumb
    
    merged_feed = []
    
    # Add news items
    for item in news_items:
        feed_item = {
            'type': 'news',
            'title': item.get('title', ''),
            'summary': item.get('summary', ''),
            'source': item.get('source', ''),
            'source_url': item.get('source_url', ''),
            'published_date': item.get('published_date', ''),
            'thumbnail_url': item.get('thumbnail_url', ''),
        }
        merged_feed.append(feed_item)
    
    # Add video ideas with thumbnails
    for idea in video_ideas:
        # Try to find matching thumbnail
        thumbnail_url = ''
        thumbnail_path = ''
        
        # Match by various keys
        match_key = idea.get('id') or idea.get('title') or idea.get('source', '')
        if match_key and match_key in thumbnail_lookup:
            thumb = thumbnail_lookup[match_key]
            thumbnail_url = thumb.get('image_url', '')
            thumbnail_path = thumb.get('local_path', '')
        
        feed_item = {
            'type': 'video_idea',
            'title': idea.get('title', ''),
            'description': idea.get('description', ''),
            'source': idea.get('source', ''),
            'source_url': idea.get('source_url', ''),
            'thumbnail_url': thumbnail_url,
            'thumbnail_path': thumbnail_path,
            'generated_date': idea.get('generated_date', ''),
        }
        merged_feed.append(feed_item)
    
    logger.info(f"Merged feed contains {len(merged_feed)} items")
    return merged_feed


def generate_feed_json(merged_data: List[Dict[str, Any]], output_file: str = None) -> None:
    """
    Generate final feed.json file from merged data.
    
    Args:
        merged_data: List of merged feed items
        output_file: Output file path (defaults to settings.FEED_FILE)
    """
    if output_file is None:
        output_file = settings.FEED_FILE
    
    feed_data = {
        'version': '1.0',
        'generated_at': '',  # Will be set by caller or timestamp
        'items': merged_data,
        'total_items': len(merged_data),
    }
    
    save_json(feed_data, output_file)
    logger.info(f"Generated feed.json with {len(merged_data)} items")


if __name__ == "__main__":
    """Command-line execution for testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_manager.py <command> [args]")
        print("Commands:")
        print("  load <file>     - Load and print JSON file")
        print("  save <file>     - Save test data to JSON file")
        print("  merge           - Merge test data files")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "load" and len(sys.argv) > 2:
        data = load_json(sys.argv[2])
        print(json.dumps(data, indent=2))
    
    elif command == "save" and len(sys.argv) > 2:
        test_data = {"test": "data", "items": [1, 2, 3]}
        save_json(test_data, sys.argv[2])
        print(f"Saved test data to {sys.argv[2]}")
    
    elif command == "merge":
        # Test merge with sample data
        news = [{"title": "Test News", "source": "test.com"}]
        ideas = [{"title": "Test Idea", "source": "test.com"}]
        thumbs = [{"title": "Test Idea", "image_url": "test.jpg"}]
        merged = merge_feeds(news, ideas, thumbs)
        print(json.dumps(merged, indent=2))
    
    else:
        print(f"Unknown command: {command}")

