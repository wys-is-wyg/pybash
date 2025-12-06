"""
Content filtering and deduplication utilities for AI News Tracker.

Handles article deduplication, quality filtering, and relevance scoring.
"""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher
from app.scripts.logger import setup_logger

logger = setup_logger(__name__)

# Keywords that indicate AI/ML relevance
AI_ML_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
    'neural network', 'llm', 'large language model', 'gpt', 'claude', 'chatgpt',
    'openai', 'anthropic', 'transformer', 'nlp', 'natural language',
    'computer vision', 'robotics', 'automation', 'algorithm', 'data science',
    'generative ai', 'genai', 'prompt engineering', 'fine-tuning', 'training',
    'model', 'inference', 'deployment', 'mlops', 'vector database', 'embedding'
]

# Keywords that indicate low relevance (garage doors, etc.)
LOW_RELEVANCE_KEYWORDS = [
    'garage door', 'opener', 'chamberlain', 'tailwind', 'meross',
    'home improvement', 'hardware store', 'diy', 'appliance'
]


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def is_duplicate(item1: Dict[str, Any], item2: Dict[str, Any], threshold: float = 0.7) -> bool:
    """
    Check if two items are duplicates based on title similarity.
    
    Args:
        item1: First item
        item2: Second item
        threshold: Similarity threshold (0.0-1.0) above which items are considered duplicates
        
    Returns:
        True if items are duplicates, False otherwise
    """
    title1 = item1.get('title', '').lower()
    title2 = item2.get('title', '').lower()
    
    if not title1 or not title2:
        return False
    
    # Check exact match
    if title1 == title2:
        return True
    
    # Check similarity
    similarity = calculate_similarity(title1, title2)
    if similarity >= threshold:
        return True
    
    # Check if one title is contained in the other (for partial matches)
    if len(title1) > 20 and len(title2) > 20:
        if title1 in title2 or title2 in title1:
            return True
    
    return False


def calculate_relevance_score(item: Dict[str, Any]) -> float:
    """
    Calculate relevance score for an article based on keywords.
    
    Args:
        item: News item dictionary
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    title = item.get('title', '').lower()
    summary = item.get('summary', '').lower()
    tags = [tag.lower() for tag in item.get('tags', [])]
    
    text = f"{title} {summary} {' '.join(tags)}"
    
    # Count AI/ML keywords
    ai_score = sum(1 for keyword in AI_ML_KEYWORDS if keyword in text)
    
    # Penalize low-relevance keywords
    low_relevance_score = sum(1 for keyword in LOW_RELEVANCE_KEYWORDS if keyword in text)
    
    # Calculate base score (0.0 to 1.0)
    # More AI keywords = higher score, but cap at 1.0
    base_score = min(ai_score * 0.2, 1.0)
    
    # Apply penalty for low-relevance keywords
    penalty = min(low_relevance_score * 0.3, 0.8)
    final_score = max(base_score - penalty, 0.0)
    
    return final_score


def calculate_summary_quality_score(item: Dict[str, Any]) -> float:
    """
    Calculate quality score based on summary structure and readability.
    
    Judging Criteria: "well structured and easy-to-consume summary article"
    
    Args:
        item: News item dictionary
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    summary = item.get('summary', '')
    title = item.get('title', '')
    
    if not summary:
        return 0.0
    
    score = 0.0
    
    # Length check: good summaries are 100-300 words
    word_count = len(summary.split())
    if 100 <= word_count <= 300:
        score += 0.4  # Optimal length
    elif 50 <= word_count < 100 or 300 < word_count <= 500:
        score += 0.2  # Acceptable length
    # Too short or too long gets 0
    
    # Structure indicators
    # Check for multiple sentences (indicates structure)
    sentence_count = summary.count('.') + summary.count('!') + summary.count('?')
    if sentence_count >= 3:
        score += 0.3  # Well-structured with multiple sentences
    
    # Check for paragraph breaks or list indicators
    if '\n' in summary or '•' in summary or '-' in summary[:50]:
        score += 0.1  # Has structure markers
    
    # Title quality (relevant to "easy-to-consume")
    if title and len(title) > 20 and len(title) < 100:
        score += 0.2  # Good title length
    
    return min(score, 1.0)


def calculate_seo_keyword_score(item: Dict[str, Any]) -> float:
    """
    Calculate SEO and keyword research value score.
    
    Judging Criteria: "pre-validated ideas based on outlier and keyword (SEO) research"
    
    Args:
        item: News item dictionary
        
    Returns:
        SEO/keyword score between 0.0 and 1.0
    """
    title = item.get('title', '').lower()
    summary = item.get('summary', '').lower()
    tags = [tag.lower() for tag in item.get('tags', [])]
    
    score = 0.0
    
    # High-value SEO keywords (trending, searchable terms)
    high_value_keywords = [
        'new', 'latest', 'update', 'release', 'announcement', 'breakthrough',
        'innovation', 'revolutionary', 'game-changing', 'cutting-edge',
        'trend', 'future', 'next-generation', 'advanced', 'state-of-the-art'
    ]
    
    text = f"{title} {summary}"
    keyword_matches = sum(1 for keyword in high_value_keywords if keyword in text)
    score += min(keyword_matches * 0.15, 0.5)  # Up to 0.5 for keyword density
    
    # Tags indicate categorization and SEO value
    if len(tags) >= 3:
        score += 0.3  # Well-tagged content
    elif len(tags) >= 1:
        score += 0.15
    
    # Outlier detection: unique/novel content
    # Check for indicators of unique content
    unique_indicators = ['first', 'only', 'exclusive', 'unprecedented', 'never before']
    if any(indicator in text for indicator in unique_indicators):
        score += 0.2  # Outlier content
    
    return min(score, 1.0)


def calculate_interest_score(item: Dict[str, Any]) -> float:
    """
    Calculate how interesting/engaging the article is.
    
    Judging Criteria: "relevant and interesting news"
    
    Args:
        item: News item dictionary
        
    Returns:
        Interest score between 0.0 and 1.0
    """
    title = item.get('title', '')
    summary = item.get('summary', '')
    source = item.get('source', '').lower()
    
    score = 0.0
    
    # Reputable sources get higher scores
    reputable_sources = ['techcrunch', 'wired', 'the verge', 'oreilly', 'arstechnica', 'ieee']
    if any(reputable in source for reputable in reputable_sources):
        score += 0.3
    
    # Title engagement indicators
    engaging_words = ['how', 'why', 'what', 'when', 'where', 'top', 'best', 'guide', 'tutorial']
    if any(word in title.lower() for word in engaging_words):
        score += 0.2
    
    # Summary completeness
    if summary and len(summary) > 150:
        score += 0.3  # Substantial content
    
    # Recency (if published_date available)
    published_date = item.get('published_date', '')
    if published_date:
        try:
            from datetime import datetime, timezone
            pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_old = (now - pub_date.replace(tzinfo=timezone.utc)).days
            if days_old <= 7:
                score += 0.2  # Recent content
        except:
            pass
    
    return min(score, 1.0)


def calculate_composite_score(item: Dict[str, Any]) -> float:
    """
    Calculate composite quality score based on all judging criteria.
    
    Judging Criteria:
    1. Relevant and interesting news
    2. Well structured and easy-to-consume summary
    3. Pre-validated ideas based on outlier and keyword (SEO) research
    
    Args:
        item: News item dictionary
        
    Returns:
        Composite score between 0.0 and 1.0
    """
    # Weighted combination of all scores
    relevance = calculate_relevance_score(item) * 0.35  # 35% weight
    quality = calculate_summary_quality_score(item) * 0.25  # 25% weight
    seo = calculate_seo_keyword_score(item) * 0.25  # 25% weight
    interest = calculate_interest_score(item) * 0.15  # 15% weight
    
    composite = relevance + quality + seo + interest
    return min(composite, 1.0)


def deduplicate_items(items: List[Dict[str, Any]], similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Remove duplicate items from a list based on title similarity.
    
    Args:
        items: List of news items
        similarity_threshold: Similarity threshold for considering items duplicates
        
    Returns:
        List of deduplicated items (keeps first occurrence of duplicates)
    """
    logger.info(f"Deduplicating {len(items)} items (threshold: {similarity_threshold})")
    
    unique_items = []
    seen_titles = set()
    
    for item in items:
        title = item.get('title', '').lower().strip()
        
        # Skip empty titles
        if not title:
            continue
        
        # Check for exact duplicates
        if title in seen_titles:
            logger.debug(f"Skipping duplicate: {title[:50]}...")
            continue
        
        # Check for similar items
        is_dup = False
        for existing in unique_items:
            if is_duplicate(item, existing, similarity_threshold):
                logger.debug(f"Skipping similar item: {title[:50]}... (similar to {existing.get('title', '')[:50]}...)")
                is_dup = True
                break
        
        if not is_dup:
            unique_items.append(item)
            seen_titles.add(title)
    
    removed = len(items) - len(unique_items)
    logger.info(f"Deduplication complete: {len(unique_items)} unique items (removed {removed} duplicates)")
    
    return unique_items


def filter_by_relevance(items: List[Dict[str, Any]], min_score: float = 0.1) -> List[Dict[str, Any]]:
    """
    Filter items by relevance score.
    
    Args:
        items: List of news items
        min_score: Minimum relevance score to keep (0.0-1.0)
        
    Returns:
        List of filtered items with relevance scores above threshold
    """
    logger.info(f"Filtering {len(items)} items by relevance (min_score: {min_score})")
    
    filtered = []
    for item in items:
        score = calculate_relevance_score(item)
        item['relevance_score'] = score
        
        if score >= min_score:
            filtered.append(item)
        else:
            logger.debug(f"Filtered out low-relevance item: {item.get('title', '')[:50]}... (score: {score:.2f})")
    
    removed = len(items) - len(filtered)
    logger.info(f"Relevance filtering complete: {len(filtered)} items kept (removed {removed} low-relevance items)")
    
    return filtered


def filter_by_composite_score(items: List[Dict[str, Any]], min_score: float = 0.2, max_items: int = 30) -> List[Dict[str, Any]]:
    """
    Filter and rank items by composite quality score, returning top N items.
    
    Args:
        items: List of news items
        min_score: Minimum composite score to keep (0.0-1.0)
        max_items: Maximum number of items to return (default: 30)
        
    Returns:
        List of top-ranked items sorted by composite score (highest first)
    """
    logger.info(f"Filtering {len(items)} items by composite score (min_score: {min_score}, max_items: {max_items})")
    
    # Calculate composite scores for all items
    scored_items = []
    for item in items:
        composite_score = calculate_composite_score(item)
        item['composite_score'] = composite_score
        item['relevance_score'] = calculate_relevance_score(item)
        item['quality_score'] = calculate_summary_quality_score(item)
        item['seo_score'] = calculate_seo_keyword_score(item)
        item['interest_score'] = calculate_interest_score(item)
        
        if composite_score >= min_score:
            scored_items.append(item)
        else:
            logger.debug(f"Filtered out low-score item: {item.get('title', '')[:50]}... (score: {composite_score:.2f})")
    
    # Sort by composite score (highest first)
    scored_items.sort(key=lambda x: x.get('composite_score', 0.0), reverse=True)
    
    # Return top N items
    top_items = scored_items[:max_items]
    
    removed = len(items) - len(top_items)
    logger.info(f"Composite filtering complete: {len(top_items)} top items selected (removed {removed} items)")
    
    if top_items:
        logger.info(f"Score range: {top_items[-1].get('composite_score', 0):.2f} - {top_items[0].get('composite_score', 0):.2f}")
    
    return top_items


def filter_and_deduplicate(items: List[Dict[str, Any]], 
                          similarity_threshold: float = 0.7,
                          min_relevance: float = 0.1,
                          max_items: int = 30) -> List[Dict[str, Any]]:
    """
    Apply deduplication, relevance filtering, and composite scoring to get top N items.
    
    Args:
        items: List of news items
        similarity_threshold: Similarity threshold for deduplication
        min_relevance: Minimum relevance score to keep
        max_items: Maximum number of items to return (default: 30)
        
    Returns:
        Filtered, deduplicated, and top-ranked list of items
    """
    logger.info(f"Applying filtering and deduplication to {len(items)} items (max_items: {max_items})")
    
    # First deduplicate
    unique_items = deduplicate_items(items, similarity_threshold)
    
    # Then filter by relevance (basic filter)
    relevant_items = filter_by_relevance(unique_items, min_relevance)
    
    # Finally, apply composite scoring and get top N
    top_items = filter_by_composite_score(relevant_items, min_score=0.2, max_items=max_items)
    
    logger.info(f"Filtering complete: {len(top_items)} top items selected")
    
    return top_items

