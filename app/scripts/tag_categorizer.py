"""
Tag categorizer for AI News Tracker.

Assigns visual tags to articles based on content analysis for Leonardo AI image generation.
"""

from typing import List, Dict, Any, Tuple


# Negative keywords that indicate non-AI/tech content (should be rejected)
# Articles with these in the TITLE should be rejected immediately, regardless of other content
TITLE_NEGATIVE_KEYWORDS = [
    "holiday", "gift guide", "gift guides", "shopping guide", "shopping",
    "christmas", "black friday", "cyber monday", "deals", "sale", "discount"
]

NEGATIVE_KEYWORDS = [
    "holiday", "gift guide", "gift guides", "shopping", "retail", "sale", "discount",
    "promo", "coupon", "best deals", "bargains", "wishlist",
    "christmas gifts", "holiday gifts",

    "fashion", "style", "outfit", "clothing", "wardrobe",
    "beauty", "makeup", "skincare", "haircare", "grooming",
    "lifestyle", "wellness",

    "food", "recipe", "recipes", "cooking", "baking",
    "restaurant", "dining", "meal", "kitchen", "chef",

    "travel", "vacation", "tourism", "flight", "hotel",
    "airline", "cruise", "resort", "destination", "beach",

    "entertainment", "celebrity", "gossip", "tv", "television",
    "movie", "film", "music", "concert", "festival",
    "gaming", "video game", "esports", "streaming",

    "politics", "election", "government", "crime", "weather",
    "forecast", "sports", "nba", "nfl", "mlb", "soccer", "olympics",
    "zodiac", "horoscope", "astrology", "animals", "pets", "wildlife",

    "real estate", "mortgage", "home improvement", "home decor",
    "decor", "interior design", "renovation", "diy", "gardening",
    "landscape", "furniture", "appliance", "garage", "kitchen hacks",

    "health", "fitness", "workout", "exercise",
    "medical", "medicine", "doctor", "hospital",
    "pharmaceutical", "drug", "vitamin", "diet", "nutrition",
    "insurance", "healthcare",

    "parenting", "children", "kids", "family", "baby", "toddler",
    "school", "education tips",

    "viral story", "life hack", "hack", "influencer",
    "trendiest", "must have", "bizarre", "cute",
    "relationship", "dating", "love", "wedding",
    
    # Multi-part articles (Part 1, Part 2, etc.)
    "(part", "part 1", "part 2", "part 3", "part 4", "part 5",
    "part one", "part two", "part three", "part four", "part five",
    "part i", "part ii", "part iii", "part iv", "part v"
]


# AI topics for article tagging
# Note: "ai" and "artificial intelligence" are excluded since all articles are AI-related
# We use more specific tags to differentiate content
AI_TOPICS = [
    # Core ML/AI concepts
    "machine learning",
    "ml",
    "deep learning",
    "neural network",
    "large language model",
    "llm",
    "generative ai",
    "genai",
    "foundation model",
    "transformer model",
    
    # Companies/Organizations
    "openai",
    "anthropic",
    "google ai",
    "deepmind",
    "meta ai",
    "nvidia",
    
    # Hardware/Compute
    "chip",
    "gpu",
    "compute",
    
    # Training/Models
    "training data",
    "training run",
    "model weights",
    "model release",
    
    # Applications
    "ai startup",
    "ai tool",
    "ai feature",
    "ai assistant",
    "automation",
    "robotics",
    "autonomous system",
    "autonomous vehicle",
    "computer vision",
    "vision model",
    "speech recognition",
    "text-to-speech",
    "image generation",
    "video generation",
    "multimodal",
    
    # Governance/Safety
    "ai regulation",
    "ai safety",
    "ai governance",
    "cybersecurity ai",
    
    # Data Science
    "data science",
    "predictive model",
]


def categorize_article(article: Dict[str, Any], min_matches: int = 1) -> Tuple[List[str], int]:
    """
    Categorize an article and assign visual tags based on content.
    
    Args:
        article: Article dictionary with 'title', 'summary', etc.
        min_score: Minimum relevance score required (default: 3). Articles below this are rejected.
        
    Returns:
        Tuple of (visual_tags list, max_score). Returns ([], 0) if article doesn't match any category well enough.
    """
    # Combine text from title, summary, and existing tags for analysis
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    existing_tags = [tag.lower() for tag in article.get('tags', [])]
    
    # Combine all text for keyword matching
    combined_text = f"{title} {summary} {' '.join(existing_tags)}"
    
    # FIRST CHECK: Reject articles with negative keywords in TITLE immediately (no override)
    # These are almost never AI-related, even if they mention "tech"
    title_lower = title.lower()
    has_title_negative = any(neg in title_lower for neg in TITLE_NEGATIVE_KEYWORDS)
    if has_title_negative:
        # logger.debug(f"Article '{title[:50]}...' has negative keywords in title - REJECTED")
        return [], 0
    
    # SECOND CHECK: Reject multi-part articles (Part 1, Part 2, etc.) - these are usually low-value
    has_part_number = any(pattern in title_lower for pattern in [
        "(part", "part 1", "part 2", "part 3", "part 4", "part 5",
        "part one", "part two", "part three", "part four", "part five",
        "part i", "part ii", "part iii", "part iv", "part v"
    ])
    if has_part_number:
        # logger.debug(f"Article '{title[:50]}...' is a multi-part article - REJECTED")
        return [], 0
    
    # THIRD CHECK: Reject articles with negative keywords in body (unless they have strong AI keywords)
    has_negative = any(neg in combined_text for neg in NEGATIVE_KEYWORDS)
    if has_negative:
        # Check if it also has strong AI keywords (might be AI-related despite negative keyword)
        # But require MULTIPLE strong AI keywords to override negative keywords (not just one mention)
        strong_ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 
                            'gpt', 'llm', 'transformer', 'algorithm', 'model', 'deep learning']
        strong_ai_count = sum(1 for ai_kw in strong_ai_keywords if ai_kw in combined_text)
        # Require at least 3 strong AI keyword mentions to override negative keywords
        if strong_ai_count < 3:
            # logger.debug(f"Article '{title[:50]}...' contains negative keywords and only {strong_ai_count} strong AI keywords (required: 3+) - REJECTED")
            return [], 0
    
    # Match article against AI topics (excluding generic "ai" since all articles are AI-related)
    matched_topics = []
    for topic in AI_TOPICS:
        topic_lower = topic.lower()
        # Check if topic appears in the text (as whole word or phrase)
        if topic_lower in combined_text:
            # Weight title matches higher
            if topic_lower in title:
                matched_topics.append((topic, 3))  # Title match = higher weight
            elif topic_lower in summary:
                matched_topics.append((topic, 2))  # Summary match = medium weight
            else:
                matched_topics.append((topic, 1))  # Other match = lower weight
    
    # If no specific topics matched, try to infer from context
    if len(matched_topics) == 0:
        # Check for common AI patterns and assign appropriate tags
        if any(kw in combined_text for kw in ['gpt', 'chatgpt', 'claude', 'gemini']):
            matched_topics.append(('large language model', 2))
        elif any(kw in combined_text for kw in ['neural', 'neuron', 'network']):
            matched_topics.append(('neural network', 2))
        elif any(kw in combined_text for kw in ['learn', 'training', 'dataset']):
            matched_topics.append(('machine learning', 2))
        elif any(kw in combined_text for kw in ['robot', 'robotic', 'autonomous']):
            matched_topics.append(('robotics', 2))
        elif any(kw in combined_text for kw in ['vision', 'image', 'photo', 'visual']):
            matched_topics.append(('computer vision', 2))
        elif any(kw in combined_text for kw in ['regulation', 'governance', 'safety', 'ethics']):
            matched_topics.append(('ai governance', 2))
        elif any(kw in combined_text for kw in ['startup', 'company', 'funding', 'valuation']):
            matched_topics.append(('ai startup', 2))
        else:
            # Last resort: use "machine learning" as default since it's the most common
            matched_topics.append(('machine learning', 1))
    
    # Check if we have enough matches
    if len(matched_topics) < min_matches:
        # logger.debug(f"Article '{title[:50]}...' matched {len(matched_topics)} topics (required: {min_matches}+) - REJECTED")
        return [], len(matched_topics)
    
    # Sort by weight (descending) and get top 1-3 tags (reduced from 5 to avoid too many tags)
    matched_topics.sort(key=lambda x: x[1], reverse=True)
    tags = [topic for topic, weight in matched_topics[:3]]  # Top 3 matching topics
    
    match_count = len(matched_topics)
    # logger.debug(f"Article '{title[:50]}...' assigned tags: {tags} (matches: {match_count})")
    return tags, match_count


def assign_visual_tags_to_articles(articles: List[Dict[str, Any]], min_matches: int = 1, filter_low_relevance: bool = True) -> List[Dict[str, Any]]:
    """
    Assign AI topic tags to a list of articles and optionally filter out low-relevance articles.
    
    Args:
        articles: List of article dictionaries
        min_matches: Minimum number of topic matches required (default: 1)
        filter_low_relevance: If True, remove articles that don't meet minimum matches (default: True)
        
    Returns:
        List of articles with 'visual_tags' and 'tag_relevance_score' fields added.
        If filter_low_relevance=True, only returns articles that meet the minimum matches.
    """
    filtered_articles = []
    rejected_count = 0
    
    for article in articles:
        tags, match_count = categorize_article(article, min_matches=min_matches)
        article['visual_tags'] = tags
        article['tag_relevance_score'] = match_count
        
        if filter_low_relevance:
            if tags and match_count >= min_matches:
                filtered_articles.append(article)
            else:
                rejected_count += 1
                title = article.get('title', 'Unknown')[:60]
                # logger.info(f"Rejected article (matches {match_count} < {min_matches}): {title}")
        else:
            # Include all articles, even if they have no tags
            filtered_articles.append(article)
    
    if filter_low_relevance and rejected_count > 0:
        # logger.info(f"Filtered out {rejected_count} low-relevance articles (below {min_matches} matches)")
        # logger.info(f"Kept {len(filtered_articles)} relevant articles")
    
    return filtered_articles

