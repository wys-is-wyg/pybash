"""
Data management utilities for AI News Tracker.

Handles JSON file operations and data merging for the pipeline.
Phase 2: Simplified merge by article_id with clean data structure.
"""

import json
import re
import html
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import settings
from app.scripts.filtering import filter_and_deduplicate
from app.scripts.tag_categorizer import assign_visual_tags_to_articles, AI_TOPICS


def generate_article_id(source_url: str) -> str:
    """
    Generate consistent article ID from source URL using MD5 hash.
    
    Args:
        source_url: The article's source URL
        
    Returns:
        16-character hexadecimal article ID
    """
    if not source_url:
        # Fallback: use timestamp hash if no URL
        import time
        source_url = str(time.time())
    return hashlib.md5(source_url.encode()).hexdigest()[:16]


def clean_html_and_entities(text: str) -> str:
    """
    Remove HTML tags and decode HTML entities from text.
    
    Args:
        text: Text that may contain HTML tags and entities
        
    Returns:
        Cleaned text without HTML tags or entities
    """
    if not text:
        return ""
    
    # First decode HTML entities (e.g., &#8217; -> ', &amp; -> &)
    text = html.unescape(text)
    
    # Remove HTML tags using regex
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up whitespace
    text = ' '.join(text.split())
    
    return text


def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(file_path)
    if not path.is_absolute():
        # Relative paths are relative to DATA_DIR
        path = settings.DATA_DIR / file_path
    
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    
    # logger.debug(f"Loading JSON from: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # logger.debug(f"Successfully loaded JSON from {path}")
        return data
    except json.JSONDecodeError as e:
        # logger.error(f"Invalid JSON in {path}: {e}")
        raise
    except Exception as e:
        # logger.error(f"Failed to load JSON from {path}: {e}")
        raise


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """
    Save JSON data to file.
    
    Args:
        data: Dictionary to save as JSON
        file_path: Output file path (relative to DATA_DIR or absolute)
        
    Raises:
        OSError: If file cannot be written
    """
    path = Path(file_path)
    if not path.is_absolute():
        # Relative paths are relative to DATA_DIR
        path = settings.DATA_DIR / file_path
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # logger.debug(f"Saving JSON to: {path}")
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # logger.info(f"Successfully saved JSON to {path}")
    except (UnicodeEncodeError, TypeError) as e:
        # If there are encoding issues, try with ensure_ascii=True to escape non-ASCII
        # logger.warning(f"Encoding issue saving JSON, retrying with ASCII encoding: {e}")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
        # logger.info(f"Successfully saved JSON to {path} (with ASCII encoding)")
    except OSError as e:
        # logger.error(f"Failed to save JSON to {path}: {e}")
        raise


def extract_video_idea_from_description(description: str) -> Dict[str, str]:
    """
    Extract clean video title and description from video_description field.
    Handles both old format (JSON embedded in description) and new format (clean fields).
    
    Args:
        description: Video description that may contain embedded JSON
        
    Returns:
        Dict with 'title' and 'description' keys
    """
    if not description:
        return {'title': '', 'description': ''}
    
    # Try to extract JSON from description (old format)
    json_match = re.search(r'\{[^{}]*"title"\s*:\s*"([^"]+)"[^{}]*\}', description, re.DOTALL)
    
    title = ''
    clean_description = ''
    
    if json_match:
        # Old format: JSON embedded in description
        try:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            title = parsed.get('title', '')
            clean_description = parsed.get('concept_summary', '')
        except:
            # Fallback: extract with regex
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_str)
            if title_match:
                title = title_match.group(1)
            concept_match = re.search(r'"concept_summary"\s*:\s*"([^"]+)"', json_str)
            if concept_match:
                clean_description = concept_match.group(1)
    else:
        # New format: description is already clean, use as-is
        clean_description = description
    
    return {
        'title': title,
        'description': clean_description
    }


def get_tag_image_url(visual_tags: List[str]) -> str:
    """
    Get tag image URL for visual tags using semantic mapping.
    
    Args:
        visual_tags: List of visual tag strings
        
    Returns:
        URL path to tag image (e.g., "/tag_images/llm.jpg")
    """
    if not visual_tags:
        return "/tag_images/generic1.jpg"
    
    # Mapping from AI_TOPICS to semantic image names
    TAG_TO_IMAGE_MAPPING = {
        "llm": "llm.jpg",
        "large language model": "llm.jpg",
        "genai": "genai.jpg",
        "generative ai": "genai.jpg",
        "neural network": "neuralnetwork.jpg",
        "computer vision": "computer_vision.jpg",
        "vision model": "computer_vision.jpg",
        "gpu": "gpu.jpg",
        "chip": "chip.jpg",
        "robotics": "robot.jpg",
        "autonomous system": "robot.jpg",
        "autonomous vehicle": "car.jpg",
        "cybersecurity ai": "cybersecurity.jpg",
        "ai regulation": "cybersecurity.jpg",
        "ai safety": "cybersecurity.jpg",
        "ai governance": "cybersecurity.jpg",
        "data science": "computer.jpg",
        "compute": "computer.jpg",
        "machine learning": "network.jpg",
        "ml": "network.jpg",
        "deep learning": "network.jpg",
        "foundation model": "network.jpg",
        "transformer model": "network.jpg",
        "nvidia": "gpu.jpg",
        "openai": "llm.jpg",
        "anthropic": "llm.jpg",
        "google ai": "llm.jpg",
        "deepmind": "neuralnetwork.jpg",
        "meta ai": "llm.jpg",
        "training data": "computer.jpg",
        "training run": "computer.jpg",
        "model weights": "network.jpg",
        "model release": "network.jpg",
        "ai startup": "web.jpg",
        "ai tool": "web.jpg",
        "ai feature": "web.jpg",
        "ai assistant": "web.jpg",
        "automation": "robot.jpg",
        "speech recognition": "computer.jpg",
        "text-to-speech": "computer.jpg",
        "image generation": "genai.jpg",
        "video generation": "genai.jpg",
        "multimodal": "genai.jpg",
        "predictive model": "network.jpg",
    }
    
    GENERIC_IMAGES = [f"generic{i}.jpg" for i in range(1, 9)]
    
    # Try to find a semantic match for the first tag
    first_tag = visual_tags[0].lower().strip()
    
    if first_tag in TAG_TO_IMAGE_MAPPING:
        return f"/tag_images/{TAG_TO_IMAGE_MAPPING[first_tag]}"
    
    # Check if any tag matches
    for tag in visual_tags:
        tag_lower = tag.lower().strip()
        if tag_lower in TAG_TO_IMAGE_MAPPING:
            return f"/tag_images/{TAG_TO_IMAGE_MAPPING[tag_lower]}"
    
    # No semantic match - use generic image based on hash for consistency
    tag_hash = int(hashlib.md5(first_tag.encode()).hexdigest(), 16)
    generic_index = tag_hash % len(GENERIC_IMAGES)
    return f"/tag_images/{GENERIC_IMAGES[generic_index]}"


def merge_feeds(
    news_items: List[Dict[str, Any]],
    video_ideas: List[Dict[str, Any]],
    thumbnails: List[Dict[str, Any]] = None,  # Deprecated - no longer used
    apply_filtering: bool = True,
    max_items: int = 30
) -> List[Dict[str, Any]]:
    """
    Simplified merge: lightweight merge by article_id.
    
    Args:
        news_items: List of news article dictionaries (from filtered_news.json + summaries.json)
        video_ideas: List of video idea dictionaries (from video_ideas.json)
        thumbnails: Deprecated - no longer used
        apply_filtering: Whether to apply deduplication and relevance filtering
        max_items: Maximum number of news items (video ideas are separate)
        
    Returns:
        List of merged feed items with unified structure
    """
    if thumbnails:
        # logger.debug(f"Ignoring {len(thumbnails)} thumbnails (deprecated)")
    
    # logger.info(f"Merging {len(news_items)} news items, {len(video_ideas)} video ideas")
    
    # Apply filtering to news items if requested
    if apply_filtering and news_items:
        # logger.info(f"Applying filtering to news items (max_items: {max_items})")
        news_items = filter_and_deduplicate(news_items, similarity_threshold=0.7, min_relevance=0.1, max_items=max_items)
    
    # Create lookup map of video ideas by article_id
    video_ideas_by_article = {}
    for idea in video_ideas:
        article_id = idea.get('article_id', '')
        if article_id:
            if article_id not in video_ideas_by_article:
                video_ideas_by_article[article_id] = []
            video_ideas_by_article[article_id].append(idea)
    
    # logger.info(f"Grouped {len(video_ideas)} video ideas into {len(video_ideas_by_article)} articles")
    
    # Assign visual tags to news items
    news_items_with_tags = assign_visual_tags_to_articles(news_items.copy())
    
    merged_feed = []
    
    # Merge news items with their video ideas
    for item in news_items_with_tags:
        article_id = item.get('article_id', '')
        visual_tags = item.get('visual_tags', [])
        thumbnail_url = get_tag_image_url(visual_tags)
        
        feed_item = {
            'type': 'news',
            'article_id': article_id,
            'title': clean_html_and_entities(item.get('title', '')),
            'summary': clean_html_and_entities(item.get('summary', '')),
            'source': item.get('source', ''),
            'source_url': item.get('source_url', ''),
            'published_date': item.get('published_date', ''),
            'thumbnail_url': thumbnail_url,
            'visual_tags': visual_tags,
            'category': 'all',  # Flat tag system
            'author': clean_html_and_entities(item.get('author', '')),
        }
        
        # Add video ideas if available
        if article_id in video_ideas_by_article:
            video_ideas_list = []
            for idea in video_ideas_by_article[article_id]:
                # Extract clean title and description
                video_data = extract_video_idea_from_description(idea.get('video_description', ''))
                video_title = video_data.get('title') or idea.get('video_title', '')
                video_desc = video_data.get('description') or idea.get('video_description', '')
                
                video_ideas_list.append({
                    'title': clean_html_and_entities(video_title),
                    'description': clean_html_and_entities(video_desc),
                })
            
            feed_item['video_ideas'] = video_ideas_list
        
        merged_feed.append(feed_item)
    
    # Add standalone video ideas (video ideas without matching news items)
    # These are video ideas that don't have a corresponding article
    processed_article_ids = {item.get('article_id') for item in news_items_with_tags}
    standalone_ideas = []
    
    for idea in video_ideas:
        article_id = idea.get('article_id', '')
        if article_id and article_id not in processed_article_ids:
            visual_tags = idea.get('visual_tags', [])
            if not visual_tags:
                # Assign tags if missing
                # Create a minimal article dict for tag assignment
                temp_article = {
                    'title': idea.get('video_title', ''),
                    'summary': idea.get('video_description', ''),
                }
                tagged = assign_visual_tags_to_articles([temp_article])
                if tagged:
                    visual_tags = tagged[0].get('visual_tags', [])
            
            thumbnail_url = get_tag_image_url(visual_tags)
            
            # Extract clean title and description
            video_data = extract_video_idea_from_description(idea.get('video_description', ''))
            video_title = video_data.get('title') or idea.get('video_title', '')
            video_desc = video_data.get('description') or idea.get('video_description', '')
            
            feed_item = {
                'type': 'video_idea',
                'article_id': article_id,
                'title': clean_html_and_entities(video_title),
                'description': clean_html_and_entities(video_desc),
                'thumbnail_url': thumbnail_url,
                'visual_tags': visual_tags,
                'category': 'all',
            }
            
            standalone_ideas.append(feed_item)
    
    if standalone_ideas:
        # logger.info(f"Adding {len(standalone_ideas)} standalone video ideas")
        merged_feed.extend(standalone_ideas)
    
    # logger.info(f"Merged feed contains {len(merged_feed)} items ({len([x for x in merged_feed if x.get('type') == 'news'])} news, {len([x for x in merged_feed if x.get('type') == 'video_idea'])} video ideas)")
    return merged_feed


def build_display_data(
    filtered_news: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]],
    video_ideas: List[Dict[str, Any]],
    max_items: int = 30
) -> Dict[str, Any]:
    """
    Build display data optimized for frontend with centralized data lookup.
    
    Structure:
    {
        "data": {
            "article_id": { /* full article data */ },
            ...
        },
        "items": [
            {
                "article_id": "...",
                "type": "news",
                "video_ideas": [...]
            },
            ...
        ]
    }
    
    Args:
        filtered_news: News items from filtered_news.json
        summaries: Summaries from summaries.json
        video_ideas: Video ideas from video_ideas.json
        max_items: Maximum number of news items
        
    Returns:
        Dictionary with 'data' lookup and 'items' array
    """
    # logger.info(f"Building display data from {len(filtered_news)} news, {len(summaries)} summaries, {len(video_ideas)} video ideas")
    
    # Create lookups by article_id
    summaries_lookup = {s.get('article_id'): s for s in summaries}
    video_ideas_by_article = {}
    for idea in video_ideas:
        article_id = idea.get('article_id', '')
        if article_id:
            if article_id not in video_ideas_by_article:
                video_ideas_by_article[article_id] = []
            video_ideas_by_article[article_id].append(idea)
    
    # Build centralized data lookup and items array
    data_lookup = {}
    display_items = []
    
    for news_item in filtered_news[:max_items]:
        article_id = news_item.get('article_id', '')
        
        # Get summary
        summary = ''
        if article_id in summaries_lookup:
            summary = summaries_lookup[article_id].get('summary', '')
        
        # Assign visual tags
        news_with_tags = assign_visual_tags_to_articles([news_item])
        visual_tags = news_with_tags[0].get('visual_tags', []) if news_with_tags else []
        thumbnail_url = get_tag_image_url(visual_tags)
        
        # Build complete article data object (stored once in data lookup)
        article_data = {
            'article_id': article_id,
            'title': clean_html_and_entities(news_item.get('title', '')),
            'summary': clean_html_and_entities(summary),
            'source_url': news_item.get('source_url', ''),
            'published_date': news_item.get('published_date', ''),
            'source': news_item.get('source', ''),
            'author': clean_html_and_entities(news_item.get('author', '')),
            'thumbnail_url': thumbnail_url,
            'visual_tags': visual_tags,
        }
        
        # Add full_summary if available
        if news_item.get('full_summary'):
            article_data['full_summary'] = clean_html_and_entities(news_item.get('full_summary'))
        
        # Add scores
        if 'trend_score' in news_item:
            article_data['trend_score'] = news_item['trend_score']
        if 'seo_score' in news_item:
            article_data['seo_score'] = news_item['seo_score']
        if 'uniqueness_score' in news_item:
            article_data['uniqueness_score'] = news_item['uniqueness_score']
        
        # Store in centralized data lookup
        data_lookup[article_id] = article_data
        
        # Build minimal display item (references article_id)
        display_item = {
            'article_id': article_id,
            'type': 'news',
        }
        
        # Get video ideas for this article
        video_ideas_list = []
        if article_id in video_ideas_by_article:
            for idea in video_ideas_by_article[article_id]:
                # New format: video_ideas.json has video_title and video_description fields directly
                # Old format: might have JSON embedded in description, use extract_video_idea_from_description
                video_title = idea.get('video_title', '')
                video_desc = idea.get('video_description', '')
                
                # If title is empty, try extracting from description (old format)
                if not video_title and video_desc:
                    video_data = extract_video_idea_from_description(video_desc)
                    video_title = video_data.get('title', '')
                    if video_data.get('description'):
                        video_desc = video_data.get('description')
                
                # Only add if we have at least a title
                if video_title:
                    video_ideas_list.append({
                        'title': clean_html_and_entities(video_title),
                        'description': clean_html_and_entities(video_desc),
                    })
        
        if video_ideas_list:
            display_item['video_ideas'] = video_ideas_list
        
        display_items.append(display_item)
    
    # logger.info(f"Built {len(display_items)} display items with {len(data_lookup)} data entries")
    
    return {
        'data': data_lookup,
        'items': display_items
    }


def generate_feed_json(merged_data: List[Dict[str, Any]], output_file: str = None) -> None:
    """
    Generate final feed.json file from merged data.
    
    Args:
        merged_data: List of merged feed items
        output_file: Output file path (defaults to settings.FEED_FILE)
    """
    if output_file is None:
        output_file = settings.FEED_FILE
    
    from datetime import datetime
    
    feed_data = {
        'version': '2.0',
        'generated_at': datetime.utcnow().isoformat(),
        'items': merged_data,
        'total_items': len(merged_data),
    }
    
    save_json(feed_data, output_file)
    # logger.info(f"Generated feed.json with {len(merged_data)} items")


if __name__ == "__main__":
    """Command-line execution for testing and pipeline."""
    import sys
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='AI News Tracker Data Manager')
    parser.add_argument('--limit', type=int, default=30, help='Maximum number of articles in feed (default: 30)')
    parser.add_argument('command', nargs='?', help='Command to execute (load, save, merge)')
    
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
        
        # logger.info(f"Running data manager in pipeline mode (feed limit: {feed_limit})")
        
        try:
            # Load all pipeline outputs
            filtered_file = settings.get_data_file_path(settings.FILTERED_NEWS_FILE)
            if filtered_file.exists():
                news_items = load_json(str(filtered_file)).get('items', [])
                # logger.info(f"Loaded {len(news_items)} filtered news items from {settings.FILTERED_NEWS_FILE}")
            else:
                # logger.warning(f"{settings.FILTERED_NEWS_FILE} not found, falling back to {settings.RAW_NEWS_FILE}")
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
            
            # Load summaries and merge by article_id
            summaries_file = settings.get_data_file_path("summaries.json")
            if summaries_file.exists():
                summaries_data = load_json(str(summaries_file)).get('items', [])
                summaries_lookup = {s.get('article_id'): s for s in summaries_data}
                for item in news_items:
                    article_id = item.get('article_id')
                    if article_id and article_id in summaries_lookup:
                        summary_item = summaries_lookup[article_id]
                        item['summary'] = summary_item.get('summary', '')
                        if 'title' not in item or not item.get('title'):
                            item['title'] = summary_item.get('title', '')
                        if 'source_url' not in item or not item.get('source_url'):
                            item['source_url'] = summary_item.get('source_url', '')
                # logger.info(f"Merged {len(summaries_lookup)} summaries into news items")
            else:
                # logger.warning("summaries.json not found, news items will not have summaries")
            
            video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
            
            # logger.info(f"Loaded {len(news_items)} news items, {len(video_ideas)} video ideas")
            
            # Merge with filtering and limit
            merged_data = merge_feeds(news_items, video_ideas, apply_filtering=True, max_items=feed_limit)
            
            # logger.info(f"Final feed contains {len(merged_data)} items ({len([x for x in merged_data if x.get('type') == 'news'])} news, {len([x for x in merged_data if x.get('type') == 'video_idea'])} video ideas)")
            
            # Generate feed.json
            feed_data = {
                'version': '2.0',
                'generated_at': datetime.utcnow().isoformat(),
                'items': merged_data,
                'total_items': len(merged_data),
            }
            save_json(feed_data, settings.FEED_FILE)
            # logger.info(f"Feed saved to {settings.FEED_FILE}")
            
            # Also generate display.json using build_display_data (new structure)
            try:
                summaries_file = settings.get_data_file_path("summaries.json")
                video_ideas_file = settings.get_data_file_path(settings.VIDEO_IDEAS_FILE)
                
                summaries = load_json(str(summaries_file)).get('items', []) if summaries_file.exists() else []
                video_ideas = load_json(str(video_ideas_file)).get('items', []) if video_ideas_file.exists() else []
                
                # Use build_display_data for display.json (optimized for frontend)
                display_result = build_display_data(news_items, summaries, video_ideas, max_items=feed_limit)
                
                display_data = {
                    'version': '2.0',
                    'generated_at': datetime.utcnow().isoformat(),
                    'data': display_result['data'],  # Centralized data lookup
                    'items': display_result['items'],  # Minimal items array
                    'total_items': len(display_result['items']),
                }
                
                display_file = settings.get_data_file_path(settings.DISPLAY_FILE)
                save_json(display_data, str(display_file))
                # logger.info(f"Display data saved to {settings.DISPLAY_FILE}")
            except Exception as e:
                # logger.warning(f"Failed to generate display.json: {e} (feed.json was created successfully)")
            
        except FileNotFoundError as e:
            # logger.error(f"Required data file not found: {e}")
            sys.exit(1)
        except Exception as e:
            # logger.error(f"Data manager failed: {e}", exc_info=True)
            sys.exit(1)
