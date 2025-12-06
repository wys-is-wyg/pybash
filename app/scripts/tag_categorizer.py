"""
Tag categorizer for AI News Tracker.

Assigns visual tags to articles based on content analysis for Leonardo AI image generation.
"""

from typing import List, Dict, Any, Tuple
from app.scripts.logger import setup_logger

logger = setup_logger(__name__)

# Negative keywords that indicate non-AI/tech content (should be rejected)
NEGATIVE_KEYWORDS = [
    "holiday", "gift guide", "shopping", "retail", "fashion", "food", "recipe",
    "travel", "vacation", "sports", "entertainment", "celebrity", "gossip",
    "weather", "forecast", "horoscope", "zodiac", "pets", "animals", "wildlife",
    "real estate", "home improvement", "diy", "gardening", "cooking", "baking",
    "garage door", "appliance", "furniture", "decor", "lifestyle", "beauty",
    "makeup", "fitness", "health", "medical", "pharmaceutical", "insurance"
]

# Visual tag categories for Leonardo AI image generation
VISUAL_TAG_CATEGORIES = {
    "ai_ml_data": {
        "name": "AI / ML / Data Themes",
        "tags": [
            "artificial intelligence core",
            "neural network nodes",
            "transformer architecture",
            "data vortices",
            "algorithmic patterns",
            "quantum compute grid",
            "parameter clusters",
            "digital brain visualization",
            "AI model topology"
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning", "ML", "neural network",
            "transformer", "GPT", "LLM", "deep learning", "algorithm", "model training",
            "data science", "quantum computing", "parameter", "topology", "architecture"
        ]
    },
    "industry_business": {
        "name": "Industry / Business / Trends",
        "tags": [
            "global market network",
            "corporate tech skyline",
            "digital economy mesh",
            "startup innovation pulse",
            "trend momentum waves",
            "financial data holograms"
        ],
        "keywords": [
            "funding", "investment", "startup", "company", "corporate", "market",
            "business", "venture capital", "IPO", "acquisition", "merger",
            "revenue", "profit", "economy", "trend", "industry"
        ]
    },
    "safety_governance": {
        "name": "Safety / Governance / Ethics",
        "tags": [
            "governance matrix",
            "encrypted governance shield",
            "ethical decision grid",
            "secure AI containment core"
        ],
        "keywords": [
            "safety", "governance", "regulation", "policy", "ethics", "ethical",
            "regulation", "compliance", "security", "privacy", "bias", "fairness",
            "responsible AI", "AI safety", "containment", "control"
        ]
    },
    "productivity_tools": {
        "name": "Productivity / Tools / Apps",
        "tags": [
            "workflow automation stream",
            "productivity circuits",
            "interface command nodes",
            "cloud app ecosystem"
        ],
        "keywords": [
            "productivity", "tool", "app", "application", "software", "SaaS",
            "workflow", "automation", "interface", "UI", "UX", "cloud",
            "platform", "service", "consumer"
        ]
    },
    "hardware_robotics": {
        "name": "Hardware / Robotics",
        "tags": [
            "robotic actuator",
            "sensor fusion map",
            "chip architecture diagram",
            "GPU compute lattice"
        ],
        "keywords": [
            "hardware", "robot", "robotic", "chip", "processor", "GPU", "CPU",
            "sensor", "actuator", "device", "hardware", "silicon", "semiconductor",
            "NVIDIA", "AMD", "Intel", "TPU"
        ]
    },
    "science_research": {
        "name": "Science & Research",
        "tags": [
            "abstract physics lattice",
            "bio-digital neuron",
            "research waveform",
            "lab intelligence network"
        ],
        "keywords": [
            "research", "study", "paper", "scientific", "science", "laboratory",
            "experiment", "discovery", "publication", "journal", "academic",
            "physics", "biology", "chemistry", "neuroscience"
        ]
    }
}


def categorize_article(article: Dict[str, Any], min_score: int = 3) -> Tuple[List[str], int]:
    """
    Categorize an article and assign visual tags based on content.
    
    Args:
        article: Article dictionary with 'title', 'summary', 'tags' (RSS tags), etc.
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
    
    # First check: reject articles with negative keywords (unless they also have strong AI keywords)
    has_negative = any(neg in combined_text for neg in NEGATIVE_KEYWORDS)
    if has_negative:
        # Check if it also has strong AI keywords (might be AI-related despite negative keyword)
        strong_ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 
                            'gpt', 'llm', 'transformer', 'algorithm', 'model', 'deep learning']
        has_strong_ai = any(ai_kw in combined_text for ai_kw in strong_ai_keywords)
        if not has_strong_ai:
            logger.debug(f"Article '{title[:50]}...' contains negative keywords and no strong AI keywords - REJECTED")
            return [], 0
    
    # Score each category based on keyword matches
    category_scores = {}
    for category_id, category_data in VISUAL_TAG_CATEGORIES.items():
        score = 0
        keywords = category_data["keywords"]
        
        # Count keyword matches (weighted by importance)
        for keyword in keywords:
            if keyword.lower() in combined_text:
                # Title matches are more important
                if keyword.lower() in title:
                    score += 3
                elif keyword.lower() in summary:
                    score += 2
                else:
                    score += 1
        
        if score > 0:
            category_scores[category_id] = score
    
    # Check if any category meets minimum score threshold
    if not category_scores:
        logger.debug(f"Article '{title[:50]}...' has no category matches - REJECTED")
        return [], 0
    
    max_score = max(category_scores.values())
    if max_score < min_score:
        logger.debug(f"Article '{title[:50]}...' score {max_score} below minimum {min_score} - REJECTED")
        return [], max_score
    
    # Select top 1-3 categories (based on scores)
    selected_categories = sorted(
        category_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]  # Top 3 categories
    
    # Assign visual tags from selected categories
    visual_tags = []
    for category_id, score in selected_categories:
        category_data = VISUAL_TAG_CATEGORIES[category_id]
        tags = category_data["tags"]
        
        # Select 1-2 tags from this category (prefer first tags)
        if len(visual_tags) == 0:
            # First category: add 1-2 tags
            visual_tags.extend(tags[:2])
        elif len(visual_tags) < 3:
            # Additional categories: add 1 tag
            visual_tags.append(tags[0])
        else:
            break
    
    # Ensure maximum 3 tags
    visual_tags = visual_tags[:3]
    
    logger.debug(f"Article '{title[:50]}...' categorized with tags: {visual_tags} (score: {max_score})")
    return visual_tags, max_score


def assign_visual_tags_to_articles(articles: List[Dict[str, Any]], min_score: int = 3, filter_low_relevance: bool = True) -> List[Dict[str, Any]]:
    """
    Assign visual tags to a list of articles and optionally filter out low-relevance articles.
    
    Args:
        articles: List of article dictionaries
        min_score: Minimum relevance score required (default: 3)
        filter_low_relevance: If True, remove articles that don't meet minimum score (default: True)
        
    Returns:
        List of articles with 'visual_tags' and 'tag_relevance_score' fields added.
        If filter_low_relevance=True, only returns articles that meet the minimum score.
    """
    filtered_articles = []
    rejected_count = 0
    
    for article in articles:
        visual_tags, max_score = categorize_article(article, min_score=min_score)
        article['visual_tags'] = visual_tags
        article['tag_relevance_score'] = max_score
        
        if filter_low_relevance:
            if visual_tags and max_score >= min_score:
                filtered_articles.append(article)
            else:
                rejected_count += 1
                title = article.get('title', 'Unknown')[:60]
                logger.info(f"Rejected article (score {max_score} < {min_score}): {title}")
        else:
            # Include all articles, even if they have no tags
            filtered_articles.append(article)
    
    if filter_low_relevance and rejected_count > 0:
        logger.info(f"Filtered out {rejected_count} low-relevance articles (below score {min_score})")
        logger.info(f"Kept {len(filtered_articles)} relevant articles")
    
    return filtered_articles

