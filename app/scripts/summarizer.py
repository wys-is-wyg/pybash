"""
Article summarization module for AI News Tracker.

Summarizes news articles using transformer-based models.
"""

from typing import List, Dict, Any
from transformers import pipeline
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles

logger = setup_logger(__name__)

# Initialize summarization pipeline (lazy loading)
_summarizer = None


def get_summarizer():
    """
    Get or initialize the summarization pipeline.
    
    Returns:
        Hugging Face summarization pipeline
    """
    global _summarizer
    if _summarizer is None:
        logger.info("Initializing summarization model...")
        try:
            _summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1  # Use CPU (-1) or GPU (0+)
            )
            logger.info("Summarization model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load summarization model: {e}")
            raise
    return _summarizer


def summarize_article(text: str, max_words: int = None) -> str:
    """
    Summarize a single article.
    
    Args:
        text: Article text to summarize
        max_words: Maximum words in summary (defaults to settings.SUMMARY_MAX_WORDS)
        
    Returns:
        Summarized text
    """
    if max_words is None:
        max_words = settings.SUMMARY_MAX_WORDS
    
    if not text or len(text.strip()) == 0:
        logger.warning("Empty text provided for summarization")
        return ""
    
    try:
        summarizer = get_summarizer()
        
        # Calculate max_length and min_length based on word count
        # Rough estimate: 1 word ≈ 1.3 tokens
        max_length = int(max_words * 1.3)
        min_length = int(settings.SUMMARY_MIN_WORDS * 1.3)
        
        logger.debug(f"Summarizing text ({len(text)} chars) to ~{max_words} words")
        
        result = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        
        summary = result[0]['summary_text'] if result else ""
        logger.debug(f"Generated summary ({len(summary)} chars)")
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize article: {e}")
        # Fallback: return first N words
        words = text.split()[:max_words]
        return " ".join(words)


def batch_summarize_news(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Summarize multiple news articles in batch.
    
    Args:
        news_items: List of news item dictionaries with 'title' and 'summary' fields
        
    Returns:
        List of news items with added 'summary' field (if not present or enhanced)
    """
    logger.info(f"Summarizing {len(news_items)} news articles")
    
    summarized_items = []
    
    for i, item in enumerate(news_items, 1):
        try:
            # Combine title and summary for better context
            title = item.get('title', '')
            existing_summary = item.get('summary', '')
            
            # Use existing summary if it's already good, otherwise summarize
            if existing_summary and len(existing_summary.split()) >= settings.SUMMARY_MIN_WORDS:
                summary = existing_summary
                logger.debug(f"Item {i}/{len(news_items)}: Using existing summary")
            else:
                # Combine title and summary for full context
                text_to_summarize = f"{title}. {existing_summary}" if existing_summary else title
                
                if not text_to_summarize.strip():
                    logger.warning(f"Item {i}/{len(news_items)}: No text to summarize")
                    summary = ""
                else:
                    summary = summarize_article(text_to_summarize)
                    logger.debug(f"Item {i}/{len(news_items)}: Generated new summary")
            
            # Create new item with summary
            summarized_item = item.copy()
            summarized_item['summary'] = summary
            summarized_item['summary_generated'] = True
            
            summarized_items.append(summarized_item)
            
        except Exception as e:
            logger.error(f"Failed to summarize item {i}/{len(news_items)}: {e}")
            # Keep original item without summary
            item_copy = item.copy()
            item_copy['summary'] = item.get('summary', '')
            item_copy['summary_generated'] = False
            summarized_items.append(item_copy)
    
    logger.info(f"Successfully summarized {len(summarized_items)} articles")
    return summarized_items


def main():
    """Main execution function for command-line invocation."""
    import sys
    
    try:
        logger.info("Starting summarization process")
        
        # Load raw news from file
        input_file = settings.RAW_NEWS_FILE
        logger.info(f"Loading news items from {input_file}")
        
        try:
            data = load_json(input_file)
            news_items = data.get('items', [])
        except FileNotFoundError:
            logger.error(f"Input file not found: {input_file}")
            return 1
        
        if not news_items:
            logger.warning("No news items to summarize")
            return 0
        
        # Assign visual tags to articles before summarizing
        logger.info("Assigning visual tags to articles...")
        news_items = assign_visual_tags_to_articles(news_items)
        
        # Summarize articles
        summarized_items = batch_summarize_news(news_items)
        
        # Save summaries
        output_file = settings.SUMMARIES_FILE
        output_data = {
            'summarized_at': '',  # Will be set by data_manager
            'total_items': len(summarized_items),
            'items': summarized_items,
        }
        save_json(output_data, output_file)
        
        logger.info("Summarization completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)

