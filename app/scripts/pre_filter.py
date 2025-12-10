"""
Pre-filter raw news articles before summarization.

Filters articles for AI relevance, removes non-AI content, and ensures only
relevant articles proceed to summarization and video idea generation.
"""

import sys
from typing import List, Dict, Any
from app.config import settings
from app.scripts.data_manager import load_json, save_json
from app.scripts.filtering import (
    filter_and_deduplicate,
    calculate_relevance_score,
    calculate_seo_keyword_score,
    calculate_interest_score
)
from app.scripts.tag_categorizer import TITLE_NEGATIVE_KEYWORDS, NEGATIVE_KEYWORDS, categorize_article


def pre_filter_articles(news_items: List[Dict[str, Any]], max_items: int = 30) -> List[Dict[str, Any]]:
    """
    Pre-filter articles before summarization.
    
    Removes:
    - Articles with negative keywords in title (holiday, gift guide, etc.)
    - Multi-part articles (Part 1, Part 2, etc.)
    - Articles that don't match AI/ML categories
    - Articles with negative keywords in body (unless strongly AI-related)
    
    Args:
        news_items: List of raw news item dictionaries
        
    Returns:
        Filtered list of AI-relevant articles
    """
    filtered_items = []
    rejected_count = 0
    rejection_reasons = {}
    
    for item in news_items:
        title = item.get('title', '').lower()
        summary = item.get('summary', '').lower()
        combined_text = f"{title} {summary}"
        
        # Check 1: Reject articles with negative keywords in TITLE
        has_title_negative = any(neg in title for neg in TITLE_NEGATIVE_KEYWORDS)
        if has_title_negative:
            rejected_count += 1
            rejection_reasons['title_negative_keywords'] = rejection_reasons.get('title_negative_keywords', 0) + 1
            continue
        
        # Check 2: Reject multi-part articles
        has_part = any(pattern in title for pattern in [
            "(part", "part 1", "part 2", "part 3", "part 4", "part 5",
            "part one", "part two", "part three", "part four", "part five",
            "part i", "part ii", "part iii", "part iv", "part v"
        ])
        if has_part:
            rejected_count += 1
            rejection_reasons['multi_part'] = rejection_reasons.get('multi_part', 0) + 1
            continue
        
        # Check 3: Categorize article - must have visual tags (AI-relevant)
        visual_tags, match_count = categorize_article(item, min_matches=1)
        if not visual_tags or match_count < 1:
            rejected_count += 1
            rejection_reasons['no_ai_category'] = rejection_reasons.get('no_ai_category', 0) + 1
            continue
        
        # Check 4: Reject articles with negative keywords in body (unless strongly AI-related)
        has_negative = any(neg in combined_text for neg in NEGATIVE_KEYWORDS)
        if has_negative:
            # Check if it has strong AI keywords to override
            strong_ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural', 
                                'gpt', 'llm', 'transformer', 'algorithm', 'model', 'deep learning']
            strong_ai_count = sum(1 for ai_kw in strong_ai_keywords if ai_kw in combined_text)
            if strong_ai_count < 3:
                rejected_count += 1
                rejection_reasons['negative_keywords'] = rejection_reasons.get('negative_keywords', 0) + 1
                continue
        
        # Article passed all checks - add visual tags and keep it
        item['visual_tags'] = visual_tags
        item['tag_relevance_score'] = match_count
        filtered_items.append(item)
    
    # Limit to top N articles by relevance score (deduplicate and rank)
    top_items = filter_and_deduplicate(filtered_items, max_items=max_items)
    
    return top_items


def main():
    """Main execution function for command-line invocation."""
    import sys
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Pre-filter news articles for AI relevance')
    parser.add_argument('--limit', type=int, default=30, help='Maximum number of articles to keep (default: 30)')
    args = parser.parse_args()
    
    try:
        # Load raw news
        raw_news_file = settings.RAW_NEWS_FILE
        raw_data = load_json(raw_news_file)
        news_items = raw_data.get('items', [])
        
        # Pre-filter articles
        filtered_items = pre_filter_articles(news_items, max_items=args.limit)
        
        # Add article_id to each filtered item, calculate scores, and keep minimal fields
        from app.scripts.data_manager import generate_article_id
        
        minimal_items = []
        for item in filtered_items:
            source_url = item.get('source_url', '')
            article_id = generate_article_id(source_url)
            
            # Prepare item for score calculation (score functions expect 'tags', we have 'visual_tags')
            score_item = item.copy()
            if 'visual_tags' in score_item and 'tags' not in score_item:
                score_item['tags'] = score_item.get('visual_tags', [])
            
            # Calculate scores (using available data: title, summary if available, tags)
            # Note: Summary might be empty at this stage, but scores can still be calculated
            relevance_score = calculate_relevance_score(score_item)
            seo_score = calculate_seo_keyword_score(score_item)
            interest_score = calculate_interest_score(score_item)
            
            # Map scores to frontend expectations:
            # - trend_score = relevance_score (how relevant/trending the topic is)
            # - seo_score = seo_score (SEO/keyword value)
            # - uniqueness_score = interest_score (how unique/interesting)
            
            # Keep only essential fields
            minimal_item = {
                'article_id': article_id,
                'title': item.get('title', ''),
                'source_url': source_url,
                'published_date': item.get('published_date', ''),
                'source': item.get('source', ''),
                'trend_score': relevance_score,
                'seo_score': seo_score,
                'uniqueness_score': interest_score,
            }
            
            # Add author if available
            if item.get('author'):
                minimal_item['author'] = item.get('author')
            
            # Add full summary from raw_news.json (for modal display)
            if item.get('summary'):
                minimal_item['full_summary'] = item.get('summary')
            
            minimal_items.append(minimal_item)
        
        # Save filtered news to filtered_news.json (don't overwrite raw_news.json)
        filtered_data = {
            'filtered_at': raw_data.get('scraped_at', ''),
            'total_items': len(minimal_items),
            'items': minimal_items,
        }
        
        filtered_news_file = settings.get_data_file_path(settings.FILTERED_NEWS_FILE)
        save_json(filtered_data, str(filtered_news_file))
        
    except Exception as e:
        from app.scripts.error_logger import log_exception
        log_exception(e, context="pre_filter.main")
        sys.exit(1)


if __name__ == "__main__":
    # Initialize error logging for this script
    from app.scripts.error_logger import initialize_error_logging
    initialize_error_logging()
    
    main()

