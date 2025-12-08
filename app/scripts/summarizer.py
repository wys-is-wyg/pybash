"""
Article summarization module for AI News Tracker.

Summarizes news articles using transformer-based models.
"""

import re
import html
from typing import List, Dict, Any
from transformers import pipeline
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles
from app.scripts.input_validator import validate_for_summarization

logger = setup_logger(__name__)

# Initialize summarization pipeline (lazy loading)
_summarizer = None


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
    
    # Remove common HTML artifacts
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#8217;', "'", text)
    text = re.sub(r'&#8230;', '...', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def get_summarizer():
    """
    Get or initialize the summarization pipeline.
    
    Returns:
        Hugging Face summarization pipeline
    """
    global _summarizer
    if _summarizer is None:
        logger.info("Initializing summarization model (this may take 1-2 minutes on first run)...")
        logger.info("Model: facebook/bart-large-cnn (~1.6GB download on first run)")
        try:
            import time
            start_time = time.time()
            
            _summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1,  # Use CPU (-1) or GPU (0+)
                model_kwargs={"cache_dir": "/app/app/models"}  # Cache model in app/models directory
            )
            
            load_time = time.time() - start_time
            logger.info(f"Summarization model loaded successfully in {load_time:.1f} seconds")
        except Exception as e:
            logger.error(f"Failed to load summarization model: {e}", exc_info=True)
            raise
    else:
        logger.debug("Using cached summarization model")
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
    
    # Validate and sanitize input before passing to Hugging Face
    is_valid, sanitized_text, reason = validate_for_summarization(text)
    if not is_valid:
        logger.error(f"Input validation failed for summarization: {reason}")
        # Return empty string rather than processing potentially dangerous input
        return ""
    
    # Use sanitized text
    text = sanitized_text
    
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
        
        # Clean HTML tags and entities from summary
        summary = clean_html_and_entities(summary)
        
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
    
    # Pre-load model before batch processing (avoids loading delay during processing)
    logger.info("Pre-loading summarization model...")
    try:
        summarizer = get_summarizer()
        logger.info("Model pre-loaded successfully, starting batch processing...")
    except Exception as e:
        logger.error(f"Failed to pre-load model: {e}", exc_info=True)
        raise
    
    summarized_items = []
    import time
    batch_start = time.time()
    
    for i, item in enumerate(news_items, 1):
        try:
            # Combine title and summary for better context
            title = item.get('title', '')
            existing_summary = item.get('summary', '')
            
            # Use existing summary if it's already good, otherwise summarize
            if existing_summary and len(existing_summary.split()) >= settings.SUMMARY_MIN_WORDS:
                summary = clean_html_and_entities(existing_summary)
                logger.debug(f"Item {i}/{len(news_items)}: Using existing summary (cleaned)")
            else:
                # Combine title and summary for full context
                text_to_summarize = f"{title}. {existing_summary}" if existing_summary else title
                
                if not text_to_summarize.strip():
                    logger.warning(f"Item {i}/{len(news_items)}: No text to summarize")
                    summary = ""
                else:
                    item_start = time.time()
                    summary = summarize_article(text_to_summarize)
                    item_time = time.time() - item_start
                    logger.info(f"Item {i}/{len(news_items)}: Generated summary in {item_time:.1f}s ({len(summary.split())} words)")
                    
                    # Log progress every 10 items
                    if i % 10 == 0:
                        elapsed = time.time() - batch_start
                        avg_time = elapsed / i
                        remaining = (len(news_items) - i) * avg_time
                        logger.info(f"Progress: {i}/{len(news_items)} ({i*100//len(news_items)}%) - Est. remaining: {remaining/60:.1f} min")
            
            # Create new item with summary
            summarized_item = item.copy()
            summarized_item['summary'] = summary
            summarized_item['summary_generated'] = True
            summarized_item['summary_method'] = 'transformers'
            
            summarized_items.append(summarized_item)
            
        except Exception as e:
            logger.error(f"Failed to summarize item {i}/{len(news_items)}: {e}")
            # Keep original item without summary
            item_copy = item.copy()
            item_copy['summary'] = item.get('summary', '')
            item_copy['summary_generated'] = False
            item_copy['summary_method'] = 'failed'
            summarized_items.append(item_copy)
    
    total_time = time.time() - batch_start
    successful = sum(1 for item in summarized_items if item.get('summary_generated', False))
    logger.info(f"Batch summarization complete: {successful}/{len(news_items)} successful in {total_time/60:.1f} minutes")
    logger.info(f"Average time per article: {total_time/len(news_items):.1f} seconds")
    
    return summarized_items


def main():
    """Main execution function for command-line invocation."""
    import sys
    import json
    
    try:
        logger.info("Starting summarization process")
        
        # Try to read from stdin first (for pipeline usage), otherwise use file
        news_items = None
        if not sys.stdin.isatty():
            # Reading from stdin (pipeline mode)
            logger.info("Reading news items from stdin")
            try:
                stdin_data = sys.stdin.read()
                if stdin_data and stdin_data.strip():
                    data = json.loads(stdin_data)
                    news_items = data.get('items', [])
                    logger.info(f"Loaded {len(news_items)} news items from stdin")
                else:
                    logger.warning("stdin is empty, falling back to file")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON from stdin: {e}")
                logger.info("Falling back to file input")
        
        # If stdin didn't work, load from file
        if news_items is None:
            input_file = settings.RAW_NEWS_FILE
            logger.info(f"Loading news items from {input_file}")
            
            try:
                data = load_json(input_file)
                news_items = data.get('items', [])
                logger.info(f"Loaded {len(news_items)} news items from file")
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
