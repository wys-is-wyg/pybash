"""
Data management utilities for AI News Tracker.

Handles JSON file operations and data merging for the pipeline.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.filtering import filter_and_deduplicate
from app.scripts.tag_categorizer import assign_visual_tags_to_articles

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
    except (UnicodeEncodeError, TypeError) as e:
        # If there are encoding issues, try with ensure_ascii=True to escape non-ASCII
        logger.warning(f"Encoding issue saving JSON, retrying with ASCII encoding: {e}")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
        logger.info(f"Successfully saved JSON to {path} (with ASCII encoding)")
    except OSError as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        raise


def merge_feeds(
    news_items: List[Dict[str, Any]],
    video_ideas: List[Dict[str, Any]],
    thumbnails: List[Dict[str, Any]] = None,  # Deprecated - no longer used
    apply_filtering: bool = True,
    max_items: int = 30
) -> List[Dict[str, Any]]:
    """
    Merge news items and video ideas into unified feed structure.
    Tag images are assigned based on visual_tags from pre-generated tag_images.
    
    Args:
        news_items: List of news article dictionaries
        video_ideas: List of video idea dictionaries
        thumbnails: Deprecated - no longer used (tag images are pre-generated)
        apply_filtering: Whether to apply deduplication and relevance filtering
        
    Returns:
        List of merged feed items with unified structure
    """
    if thumbnails is None:
        thumbnails = []
    logger.info(f"Merging {len(news_items)} news items, {len(video_ideas)} video ideas (using pre-generated tag images)")
    
    # Apply filtering and deduplication to news items
    # Reserve some slots for video ideas (30% of max_items, minimum 1)
    video_idea_slots = max(1, int(max_items * 0.3))
    news_slots = max_items - video_idea_slots
    
    if apply_filtering and news_items:
        logger.info(f"Applying filtering and deduplication to news items (max_items: {max_items}, news_slots: {news_slots}, video_idea_slots: {video_idea_slots})")
        # Get top N best articles based on composite scoring (reserve slots for video ideas)
        news_items = filter_and_deduplicate(news_items, similarity_threshold=0.7, min_relevance=0.1, max_items=news_slots)
    
    # Create thumbnail lookup by video idea ID or title
    thumbnail_lookup = {}
    for thumb in thumbnails:
        # Match thumbnails to video ideas by ID, title, or source
        key = thumb.get('video_idea_id') or thumb.get('title') or thumb.get('source', '')
        if key:
            thumbnail_lookup[key] = thumb
    
    merged_feed = []
    
    # Assign visual tags to news items before adding to feed
    news_items_with_tags = assign_visual_tags_to_articles(news_items.copy())
    
    # Load tag images metadata for news items too
    tag_images_metadata = {}
    tag_images_dir = settings.DATA_DIR / "tag_images"
    tag_metadata_file = tag_images_dir / "tag_images_metadata.json"
    
    if tag_metadata_file.exists():
        try:
            tag_metadata = load_json(str(tag_metadata_file))
            for img in tag_metadata.get("images", []):
                tag = img.get("tag", "")
                if tag:
                    tag_images_metadata[tag] = img
            logger.info(f"Loaded {len(tag_images_metadata)} tag images from metadata")
        except Exception as e:
            logger.warning(f"Failed to load tag images metadata: {e}")
    
    # Function to get tag image for a visual tag
    def get_tag_image(visual_tags: List[str]) -> str:
        """Get a tag image URL for the first matching visual tag."""
        if not visual_tags:
            logger.debug("No visual tags provided for image lookup")
            # Fallback: pick a random tag image if available
            if tag_images_metadata:
                import random
                random_img = random.choice(list(tag_images_metadata.values()))
                filename = random_img.get("filename", "")
                if filename:
                    logger.debug(f"Using random tag image: {filename}")
                    return f"/api/tag-images/{filename}"
            return ""
        
        if not tag_images_metadata:
            logger.warning("No tag images metadata loaded")
            return ""
        
        # Try to find image for first visual tag (exact match)
        for tag in visual_tags:
            if tag in tag_images_metadata:
                img_data = tag_images_metadata[tag]
                filename = img_data.get("filename", "")
                if filename:
                    logger.debug(f"Found exact match for tag '{tag}': {filename}")
                    return f"/api/tag-images/{filename}"
        
        # If no exact match, pick a random tag image
        if tag_images_metadata:
            import random
            random_img = random.choice(list(tag_images_metadata.values()))
            filename = random_img.get("filename", "")
            if filename:
                logger.debug(f"No exact match for tags {visual_tags}, using random: {filename}")
                return f"/api/tag-images/{filename}"
        
        logger.warning(f"No tag image found for visual tags: {visual_tags}")
        return ""
    
    # Helper function to get category from visual tags (deprecated - tags are now flat)
    def get_category_from_tags(visual_tags: List[str]) -> str:
        """Get category - now just returns 'all' since we use flat tags."""
        return "all"  # Categories removed, using flat tag system
    
    # Add news items (with tags preserved)
    for item in news_items_with_tags:
        visual_tags = item.get('visual_tags', [])
        thumbnail_url = get_tag_image(visual_tags)
        category = get_category_from_tags(visual_tags)
        
        feed_item = {
            'type': 'news',
            'title': item.get('title', ''),
            'summary': item.get('summary', ''),
            'source': item.get('source', ''),
            'source_url': item.get('source_url', ''),
            'published_date': item.get('published_date', ''),
            'thumbnail_url': thumbnail_url,
            'visual_tags': visual_tags,  # Only visual tags from categorization
            'category': category,  # Category ID for filtering
            'author': item.get('author', ''),
        }
        merged_feed.append(feed_item)
    
    # Add video ideas with tag images (limit to reserved slots)
    video_ideas_to_add = video_ideas[:video_idea_slots] if len(video_ideas) > video_idea_slots else video_ideas
    logger.info(f"Adding {len(video_ideas_to_add)} video ideas (out of {len(video_ideas)} available)")
    
    for idea in video_ideas_to_add:
        # Get visual tags for this idea
        visual_tags = idea.get('visual_tags', [])
        
        # Get tag image based on visual tags
        thumbnail_http_url = get_tag_image(visual_tags)
        
        # Get category from visual tags
        category = get_category_from_tags(visual_tags)
        
        feed_item = {
            'type': 'video_idea',
            'title': idea.get('title', ''),
            'description': idea.get('description', ''),
            'source': idea.get('source', ''),
            'source_url': idea.get('source_url', ''),
            'thumbnail_url': thumbnail_http_url,  # Tag image URL
            'generated_date': idea.get('generated_date', ''),
            'tags': idea.get('tags', []),  # Preserve tags if available
            'visual_tags': visual_tags,  # Preserve visual tags
            'category': category,  # Category ID for filtering
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
    """Command-line execution for testing and pipeline."""
    import sys
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='AI News Tracker Data Manager')
    parser.add_argument('--limit', type=int, default=30, help='Maximum number of articles in feed (default: 30)')
    parser.add_argument('command', nargs='?', help='Command to execute (load, save, merge)')
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['load', 'save', 'merge']:
        # Old-style command parsing for backward compatibility
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
    else:
        # New-style: pipeline mode with --limit flag
        args = parser.parse_args()
        feed_limit = args.limit
        
        logger.info(f"Running data manager in pipeline mode (feed limit: {feed_limit})")
        
        try:
            # Load all pipeline outputs
            news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
            video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
            
            # Thumbnails are optional (deprecated - using pre-generated tag images now)
            thumbnails = []
            if Path(settings.THUMBNAILS_FILE).exists():
                thumbnails = load_json(settings.THUMBNAILS_FILE).get('items', [])
                logger.info(f"Loaded {len(thumbnails)} thumbnails (deprecated - using tag images)")
            else:
                logger.info("No thumbnails.json found (using pre-generated tag images)")
            
            logger.info(f"Loaded {len(news_items)} news items, {len(video_ideas)} video ideas")
            
            # Merge with filtering and limit
            merged_data = merge_feeds(news_items, video_ideas, thumbnails, apply_filtering=True, max_items=feed_limit)
            
            # Ensure final feed doesn't exceed limit (in case video ideas added extra items)
            if len(merged_data) > feed_limit:
                logger.info(f"Limiting final feed from {len(merged_data)} to {feed_limit} items")
                merged_data = merged_data[:feed_limit]
            
            # Generate feed.json
            feed_data = {
                'version': '1.0',
                'generated_at': datetime.utcnow().isoformat(),
                'items': merged_data,
                'total_items': len(merged_data),
            }
            save_json(feed_data, settings.FEED_FILE)
            
            logger.info(f"Successfully generated feed.json with {len(merged_data)} items")
            print(f"✓ Feed generated: {len(merged_data)} items (limit: {feed_limit})")
            
        except FileNotFoundError as e:
            logger.error(f"Required data file not found: {e}")
            print(f"Error: Required data file not found: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error in data manager: {e}", exc_info=True)
            print(f"Error: {e}")
            sys.exit(1)

