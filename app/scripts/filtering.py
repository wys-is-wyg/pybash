"""
Content filtering and deduplication utilities for AI News Tracker.

Handles article deduplication, quality filtering, and relevance scoring.
"""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher
from app.scripts.tag_categorizer import TITLE_NEGATIVE_KEYWORDS, NEGATIVE_KEYWORDS


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
    Requires articles to be more than 50% about AI/ML to pass.
    
    Args:
        item: News item dictionary
        
    Returns:
        Relevance score between 0.0 and 1.0 (0.0 if < 50% AI content)
    """
    title = item.get('title', '').lower()
    summary = item.get('summary', '').lower()
    tags = [tag.lower() for tag in item.get('tags', [])]
    
    # Combine all text
    text = f"{title} {summary} {' '.join(tags)}"
    
    # Split into words (remove punctuation, keep only alphanumeric)
    words = re.findall(r'\b[a-z]+\b', text)
    
    # Filter out common stop words that don't indicate topic
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'it', 'its', 'they', 'them', 'their', 'we', 'our', 'you', 'your', 'he', 'she', 'his', 'her',
        'from', 'as', 'not', 'if', 'then', 'than', 'more', 'most', 'some', 'any', 'all', 'each', 'every',
        'which', 'what', 'when', 'where', 'why', 'how', 'who', 'whom', 'whose'
    }
    
    # Get significant words (non-stop words)
    significant_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    if len(significant_words) == 0:
        # No significant words, reject
        return 0.0
    
    # Count how many significant words are AI-related
    # Use a more precise matching: check if the word is part of an AI keyword phrase
    ai_word_count = 0
    ai_keyword_phrases_found = set()
    
    for keyword in AI_ML_KEYWORDS:
        # Check if the full keyword phrase appears in the text
        if keyword in text:
            # Count how many words from this keyword phrase are in significant_words
            keyword_words = keyword.split()
            for kw_word in keyword_words:
                if kw_word in significant_words:
                    ai_word_count += 1
                    ai_keyword_phrases_found.add(keyword)
    
    # Also check individual significant words that might be AI-related
    for word in significant_words:
        # Skip if already counted as part of a phrase
        if any(word in phrase for phrase in ai_keyword_phrases_found):
            continue
        # Check if word matches any AI keyword (as substring or exact match)
        for keyword in AI_ML_KEYWORDS:
            if keyword in word or word in keyword:
                ai_word_count += 1
                break
    
    # Calculate AI percentage
    ai_percentage = ai_word_count / len(significant_words) if len(significant_words) > 0 else 0.0
    
    # Count AI/ML keyword mentions (for scoring and relevance check)
    ai_keyword_mentions = sum(1 for keyword in AI_ML_KEYWORDS if keyword in text)
    
    # Check if article has meaningful AI relevance
    # If tag_relevance_score >= 1, it means the article matched AI topics, so trust that and be lenient
    tag_relevance_score = item.get('tag_relevance_score', 0)
    if tag_relevance_score >= 1:
        # Very lenient check: if article has tag_relevance_score >= 1, it already matched AI topics
        # Just verify there's at least 1 AI keyword mention (tag_relevance_score already indicates AI relevance)
        if ai_keyword_mentions < 1:
            # logger.debug(f"Article '{item.get('title', '')[:50]}...' has tag_relevance_score={tag_relevance_score} but no AI keywords found - REJECTED")
            return 0.0
        # For articles with tag_relevance_score >= 1, calculate a score based on AI keyword density
        # but don't reject if percentage is low - trust the tag_relevance_score
    else:
        # Strict: require > 50% AI content for articles without tag_relevance_score
        if ai_percentage < 0.5:
            # logger.debug(f"Article '{item.get('title', '')[:50]}...' has {ai_percentage:.1%} AI content (required: >50%) - REJECTED")
            return 0.0
    
    # Penalize low-relevance keywords
    low_relevance_score = sum(1 for keyword in LOW_RELEVANCE_KEYWORDS if keyword in text)
    
    # Calculate base score (0.0 to 1.0) based on AI keyword density
    # More AI keywords = higher score, but cap at 1.0
    base_score = min(ai_keyword_mentions * 0.15, 1.0)
    
    # Boost score based on AI percentage
    if tag_relevance_score >= 1:
        # For articles with tag_relevance_score >= 1, give bonus even if percentage is low
        # Minimum bonus of 0.1 for having tag_relevance_score >= 1
        ai_bonus = max((ai_percentage - 0.1) * 0.3, 0.1)  # At least 0.1 bonus, up to 0.27 for 100% AI
    else:
        # For articles without tag_relevance_score, require > 50% for bonus
        ai_bonus = (ai_percentage - 0.5) * 0.5  # Up to 0.25 bonus for 100% AI
    
    # Apply penalty for low-relevance keywords
    penalty = min(low_relevance_score * 0.3, 0.8)
    final_score = max(base_score + ai_bonus - penalty, 0.0)
    
    # Ensure articles with tag_relevance_score >= 1 get at least a small score if they have AI keywords
    if tag_relevance_score >= 1 and ai_keyword_mentions >= 1:
        final_score = max(final_score, 0.05)  # Minimum score of 0.05 for articles with tag_relevance_score >= 1
    
    return min(final_score, 1.0)


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
    # logger.info(f"Deduplicating {len(items)} items (threshold: {similarity_threshold})")
    
    unique_items = []
    seen_titles = set()
    
    for item in items:
        title = item.get('title', '').lower().strip()
        
        # Skip empty titles
        if not title:
            continue
        
        # Check for exact duplicates
        if title in seen_titles:
            # logger.debug(f"Skipping duplicate: {title[:50]}...")
            continue
        
        # Check for similar items
        is_dup = False
        for existing in unique_items:
            if is_duplicate(item, existing, similarity_threshold):
                # logger.debug(f"Skipping similar item: {title[:50]}... (similar to {existing.get('title', '')[:50]}...)")
                is_dup = True
                break
        
        if not is_dup:
            unique_items.append(item)
            seen_titles.add(title)
    
    removed = len(items) - len(unique_items)
    # logger.info(f"Deduplication complete: {len(unique_items)} unique items (removed {removed} duplicates)")
    
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
    # logger.info(f"Filtering {len(items)} items by relevance (min_score: {min_score})")
    
    filtered = []
    for item in items:
        score = calculate_relevance_score(item)
        item['relevance_score'] = score
        
        if score >= min_score:
            filtered.append(item)
        else:
            # logger.debug(f"Filtered out low-relevance item: {item.get('title', '')[:50]}... (score: {score:.2f})")
    
    removed = len(items) - len(filtered)
    # logger.info(f"Relevance filtering complete: {len(filtered)} items kept (removed {removed} low-relevance items)")
    
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
    # logger.info(f"Filtering {len(items)} items by composite score (min_score: {min_score}, max_items: {max_items})")
    
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
            # logger.debug(f"Filtered out low-score item: {item.get('title', '')[:50]}... (score: {composite_score:.2f})")
    
    # Sort by composite score (highest first)
    scored_items.sort(key=lambda x: x.get('composite_score', 0.0), reverse=True)
    
    # Return top N items
    top_items = scored_items[:max_items]
    
    removed = len(items) - len(top_items)
    # logger.info(f"Composite filtering complete: {len(top_items)} top items selected (removed {removed} items)")
    
    if top_items:
        # logger.info(f"Score range: {top_items[-1].get('composite_score', 0):.2f} - {top_items[0].get('composite_score', 0):.2f}")
    
    return top_items


def filter_by_user_criteria(items: List[Dict[str, Any]], max_items: int = 30) -> List[Dict[str, Any]]:
    """
    Filter items using user's criteria:
    - tag_relevance_score >= 1
    - relevance_to_ai > 50% (relevance_score > 0.0, since calculate_relevance_score returns 0.0 if < 50%)
    - No negative keywords
    
    Args:
        items: List of news items
        max_items: Maximum number of items to return (default: 30)
        
    Returns:
        Filtered list of items that meet user criteria, sorted by relevance_score (highest first)
    """
    # logger.info(f"Filtering {len(items)} items by user criteria (tag_relevance_score >= 1, relevance_to_ai > 50%, no negative keywords)")
    
    filtered_items = []
    rejected_count = 0
    rejection_reasons = {}
    
    for item in items:
        # Check 1: tag_relevance_score >= 1
        tag_relevance_score = item.get('tag_relevance_score', 0)
        if tag_relevance_score < 1:
            rejected_count += 1
            rejection_reasons['tag_relevance_score'] = rejection_reasons.get('tag_relevance_score', 0) + 1
            # logger.debug(f"Rejected '{item.get('title', '')[:50]}...' - tag_relevance_score {tag_relevance_score} < 1")
            continue
        
        # Check 2: relevance_to_ai > 50% (relevance_score > 0.0)
        relevance_score = calculate_relevance_score(item)
        item['relevance_score'] = relevance_score
        if relevance_score <= 0.0:
            rejected_count += 1
            rejection_reasons['relevance_to_ai'] = rejection_reasons.get('relevance_to_ai', 0) + 1
            # logger.debug(f"Rejected '{item.get('title', '')[:50]}...' - relevance_to_ai <= 50% (score: {relevance_score:.2f})")
            continue
        
        # Check 3: No negative keywords in title
        title = item.get('title', '').lower()
        has_title_negative = any(neg in title for neg in TITLE_NEGATIVE_KEYWORDS)
        if has_title_negative:
            rejected_count += 1
            rejection_reasons['title_negative_keywords'] = rejection_reasons.get('title_negative_keywords', 0) + 1
            # logger.debug(f"Rejected '{item.get('title', '')[:50]}...' - negative keywords in title")
            continue
        
        # Check 4: No negative keywords in body (unless strongly AI-related)
        summary = item.get('summary', '').lower()
        combined_text = f"{title} {summary}"
        has_negative = any(neg in combined_text for neg in NEGATIVE_KEYWORDS)
        if has_negative:
            # Check if it has strong AI keywords to override
            strong_ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 
                                'gpt', 'llm', 'transformer', 'algorithm', 'model', 'deep learning']
            strong_ai_count = sum(1 for ai_kw in strong_ai_keywords if ai_kw in combined_text)
            if strong_ai_count < 3:
                rejected_count += 1
                rejection_reasons['negative_keywords'] = rejection_reasons.get('negative_keywords', 0) + 1
                # logger.debug(f"Rejected '{item.get('title', '')[:50]}...' - negative keywords, only {strong_ai_count} AI keywords")
                continue
        
        # Item passed all checks
        filtered_items.append(item)
    
    # Sort by relevance_score (highest first)
    filtered_items.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
    
    # Return top N items
    top_items = filtered_items[:max_items]
    
    removed = len(items) - len(top_items)
    # logger.info(f"User criteria filtering complete: {len(top_items)} items kept (removed {removed} items)")
    if rejection_reasons:
        # logger.info(f"Rejection reasons: {rejection_reasons}")
    
    if top_items:
        # logger.info(f"Relevance score range: {top_items[-1].get('relevance_score', 0):.2f} - {top_items[0].get('relevance_score', 0):.2f}")
    
    return top_items


def filter_and_deduplicate(items: List[Dict[str, Any]], 
                          similarity_threshold: float = 0.7,
                          min_relevance: float = 0.1,
                          max_items: int = 30) -> List[Dict[str, Any]]:
    """
    Apply deduplication and filtering using user's criteria to get top N items.
    
    User criteria:
    - tag_relevance_score >= 1
    - relevance_to_ai > 50% (relevance_score > 0.0)
    - No negative keywords
    
    Args:
        items: List of news items
        similarity_threshold: Similarity threshold for deduplication
        min_relevance: Minimum relevance score to keep (deprecated, kept for compatibility)
        max_items: Maximum number of items to return (default: 30)
        
    Returns:
        Filtered, deduplicated, and top-ranked list of items
    """
    # logger.info(f"Applying filtering and deduplication to {len(items)} items (max_items: {max_items})")
    
    # First deduplicate
    unique_items = deduplicate_items(items, similarity_threshold)
    
    # Then filter by user criteria (tag_relevance_score >= 1, relevance_to_ai > 50%, no negative keywords)
    top_items = filter_by_user_criteria(unique_items, max_items=max_items)
    
    # logger.info(f"Filtering complete: {len(top_items)} top items selected")
    
    return top_items

