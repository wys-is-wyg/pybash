"""
Article summarization module for AI News Tracker.

Summarizes news articles using fast extractive summarization (sumy library).
Falls back to transformers if sumy is not available.
"""

import re
import html
from typing import List, Dict, Any, Optional
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles
from app.scripts.input_validator import validate_for_summarization

logger = setup_logger(__name__)

# Try to import sumy for fast extractive summarization
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.text_rank import TextRankSummarizer
    from sumy.nlp.stemmers import Stemmer
    from sumy.utils import get_stop_words
    
    # Download required NLTK data for sumy
    try:
        import nltk
        import os
        
        # Set NLTK data directory to app/data/nltk_data (persistent across container restarts)
        nltk_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'nltk_data')
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.data.path.insert(0, nltk_data_dir)
        
        # Download punkt_tab tokenizer if not already present
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            logger.info("Downloading NLTK punkt_tab tokenizer (required for sumy)...")
            nltk.download('punkt_tab', quiet=True, download_dir=nltk_data_dir)
            logger.info("NLTK punkt_tab downloaded successfully")
        
        # Download stopwords if not already present
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True, download_dir=nltk_data_dir)
            logger.info("NLTK stopwords downloaded successfully")
            
    except Exception as e:
        logger.warning(f"Failed to download NLTK data: {e}, sumy may not work correctly")
    
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False
    logger.warning("sumy not available, will use transformers fallback")

# Initialize transformers summarizer (fallback, lazy loading)
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
    Get or initialize the transformers summarization pipeline (fallback only).
    
    Returns:
        Hugging Face summarization pipeline (only used if sumy is not available)
    """
    global _summarizer
    if _summarizer is None:
        logger.info("Initializing transformers summarization model (fallback)...")
        logger.info("Model: facebook/bart-large-cnn (~1.6GB download on first run)")
        try:
            from transformers import pipeline
            import time
            start_time = time.time()
            
            _summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1,  # Use CPU (-1) or GPU (0+)
                model_kwargs={"cache_dir": "/app/app/models"}  # Cache model in app/models directory
            )
            
            load_time = time.time() - start_time
            logger.info(f"Transformers model loaded successfully in {load_time:.1f} seconds")
        except Exception as e:
            logger.error(f"Failed to load transformers model: {e}", exc_info=True)
            raise
    else:
        logger.debug("Using cached transformers model")
    return _summarizer


def summarize_with_sumy(text: str, max_words: int = 150, language: str = "english") -> str:
    """
    Fast extractive summarization using sumy TextRank algorithm.
    
    Args:
        text: Article text to summarize
        max_words: Maximum words in summary
        language: Language code (default: "english")
        
    Returns:
        Summarized text (extracted sentences)
    """
    if not SUMY_AVAILABLE:
        return None
    
    try:
        # Parse text
        parser = PlaintextParser.from_string(text, Tokenizer(language))
        stemmer = Stemmer(language)
        
        # Create summarizer
        summarizer = TextRankSummarizer(stemmer)
        summarizer.stop_words = get_stop_words(language)
        
        # Calculate number of sentences to extract (rough estimate: 15 words per sentence)
        num_sentences = max(1, max_words // 15)
        
        # Summarize
        summary_sentences = summarizer(parser.document, num_sentences)
        
        # Join sentences
        summary = " ".join(str(sentence) for sentence in summary_sentences)
        
        # Trim to max_words if needed
        words = summary.split()
        if len(words) > max_words:
            summary = " ".join(words[:max_words])
        
        return summary
        
    except Exception as e:
        logger.warning(f"sumy summarization failed: {e}, falling back to transformers")
        return None


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
        import time
        
        # Try fast sumy summarization first
        if SUMY_AVAILABLE:
            logger.debug(f"Using sumy for fast extractive summarization ({len(text)} chars)")
            start_time = time.time()
            summary = summarize_with_sumy(text, max_words=max_words)
            if summary:
                elapsed = time.time() - start_time
                logger.info(f"sumy summarization completed in {elapsed:.2f} seconds")
                summary = clean_html_and_entities(summary)
                return summary
            else:
                logger.warning("sumy failed, falling back to transformers")
        
        # Fallback to transformers (slow)
        logger.debug(f"Using transformers summarization ({len(text)} chars)")
        summarizer = get_summarizer()
        
        # Calculate max_length and min_length based on word count
        # Rough estimate: 1 word ≈ 1.3 tokens
        max_length = int(max_words * 1.3)
        min_length = int(settings.SUMMARY_MIN_WORDS * 1.3)
        
        logger.info(f"Calling transformers with max_length={max_length}, min_length={min_length}")
        
        start_time = time.time()
        result = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        elapsed = time.time() - start_time
        logger.info(f"Transformers call completed in {elapsed:.1f} seconds")
        
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
    
    # Pre-load transformers model only if sumy is not available
    if not SUMY_AVAILABLE:
        logger.info("Pre-loading transformers model (sumy not available)...")
        try:
            summarizer = get_summarizer()
            logger.info("Transformers model pre-loaded successfully, starting batch processing...")
        except Exception as e:
            logger.error(f"Failed to pre-load transformers model: {e}", exc_info=True)
            raise
    else:
        logger.info("Using fast sumy extractive summarization (no model loading needed)")
    
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
        
        # If stdin didn't work, load from filtered_news.json (pre-filtered top 30)
        if news_items is None:
            # Try filtered_news.json first (guaranteed to be filtered to top 30)
            filtered_file = settings.DATA_DIR / "filtered_news.json"
            input_file = str(filtered_file)
            logger.info(f"Loading news items from {input_file} (pre-filtered)")
            
            try:
                data = load_json(input_file)
                news_items = data.get('items', [])
                logger.info(f"Loaded {len(news_items)} news items from filtered file")
            except FileNotFoundError:
                # Fallback to raw_news.json if filtered_news.json doesn't exist
                logger.warning(f"Filtered file not found, falling back to {settings.RAW_NEWS_FILE}")
                input_file = settings.RAW_NEWS_FILE
                data = load_json(input_file)
                news_items = data.get('items', [])
                logger.info(f"Loaded {len(news_items)} news items from raw file")
        
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
