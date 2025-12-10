"""
Article summarization module for AI News Tracker.

Summarizes news articles using fast extractive summarization (sumy library).
Falls back to transformers if sumy is not available.
"""

import re
import html
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.config import settings
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles
from app.scripts.input_validator import validate_for_summarization
from app.scripts.cache_manager import cached, get_cached, set_cached

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
            nltk.download('punkt_tab', quiet=True, download_dir=nltk_data_dir)
        
        # Download stopwords if not already present
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True, download_dir=nltk_data_dir)
            
    except Exception:
        pass
    
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False

# Initialize transformers summarizer (fallback, lazy loading) - cached per process
_summarizer = None


@cached("summarizer", ttl=None, max_size=1)  # Cache summarizer (no expiration, single instance)
def get_summarizer():
    """
    Get or initialize the transformers summarization pipeline (fallback only).
    
    Uses both module-level global cache and decorator cache for maximum efficiency.
    
    Returns:
        Hugging Face summarization pipeline (only used if sumy is not available)
    """
    global _summarizer
    
    # Check module-level cache first (fastest)
    if _summarizer is not None:
        return _summarizer
    
    # Check decorator cache
    cached_summarizer = get_cached("summarizer")
    if cached_summarizer is not None:
        _summarizer = cached_summarizer
        return cached_summarizer
    
    try:
        from transformers import pipeline
        import time
        start_time = time.time()
        
        summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=-1,  # Use CPU (-1) or GPU (0+)
            model_kwargs={"cache_dir": "/app/app/models"}  # Cache model in app/models directory
        )
        
        load_time = time.time() - start_time
        
        # Store in both caches
        _summarizer = summarizer
        set_cached("summarizer", summarizer, ttl=None)
        
        return summarizer
    except Exception as e:
        pass
        raise


def clean_html_and_entities(text: str) -> str:
    """
    Remove HTML tags and decode HTML entities from text.
    Uses BeautifulSoup for better HTML parsing, extracting only text content.
    
    Args:
        text: Text that may contain HTML tags and entities
        
    Returns:
        Cleaned text without HTML tags or entities
    """
    if not text:
        return ""
    
    try:
        # Parse HTML with BeautifulSoup for better extraction
        soup = BeautifulSoup(text, 'html.parser')
        
        # Remove script, style, code, and pre elements completely
        for element in soup(["script", "style", "code", "pre", "img"]):
            element.decompose()
        
        # Get text content (this automatically removes all tags)
        text = soup.get_text(separator=' ', strip=True)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception:
        # Fallback to regex-based cleaning if BeautifulSoup fails
        # First decode HTML entities
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
        
    except Exception:
        # Expected failure - sumy not available or failed, fallback to transformers
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
        return ""
    
    # Validate and sanitize input before passing to Hugging Face
    is_valid, sanitized_text, reason = validate_for_summarization(text)
    if not is_valid:
        # Return empty string rather than processing potentially dangerous input
        return ""
    
    # Use sanitized text
    text = sanitized_text
    
    try:
        import time
        
        # Try fast sumy summarization first
        if SUMY_AVAILABLE:
            start_time = time.time()
            summary = summarize_with_sumy(text, max_words=max_words)
            if summary:
                elapsed = time.time() - start_time
                summary = clean_html_and_entities(summary)
                return summary
        
        # Fallback to transformers (slow)
        summarizer = get_summarizer()
        
        # Calculate max_length and min_length based on word count
        # Rough estimate: 1 word ≈ 1.3 tokens
        max_length = int(max_words * 1.3)
        min_length = int(settings.SUMMARY_MIN_WORDS * 1.3)
        
        start_time = time.time()
        result = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        elapsed = time.time() - start_time
        
        summary = result[0]['summary_text'] if result else ""
        
        # Clean HTML tags and entities from summary
        summary = clean_html_and_entities(summary)
        
        return summary
        
    except Exception as e:
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
    # Pre-load transformers model only if sumy is not available
    summarized_items = []
    if not SUMY_AVAILABLE:
        try:
            summarizer = get_summarizer()
        except Exception as e:
            raise
    
    import time
    batch_start = time.time()
    
    for i, item in enumerate(news_items, 1):
        try:
            # Combine title and summary for better context
            title = item.get('title', '')
            # Check for both 'summary' and 'full_summary' fields (filtered_news.json uses 'full_summary')
            existing_summary = item.get('full_summary', '') or item.get('summary', '')
            
            # Clean HTML from existing summary if present
            if existing_summary:
                existing_summary = clean_html_and_entities(existing_summary)
            
            # Use existing summary if it's already good, otherwise summarize
            if existing_summary and len(existing_summary.split()) >= settings.SUMMARY_MIN_WORDS:
                summary = existing_summary
            else:
                # Combine title and summary for full context
                text_to_summarize = f"{title}. {existing_summary}" if existing_summary else title
                
                if not text_to_summarize.strip():
                    summary = ""
                else:
                    item_start = time.time()
                    summary = summarize_article(text_to_summarize)
                    item_time = time.time() - item_start
            
            # Create new item with summary
            summarized_item = item.copy()
            summarized_item['summary'] = summary
            summarized_item['summary_generated'] = True
            summarized_item['summary_method'] = 'transformers'
            
            summarized_items.append(summarized_item)
            
        except Exception as e:
            # Keep original item without summary
            item_copy = item.copy()
            item_copy['summary'] = item.get('summary', '')
            item_copy['summary_generated'] = False
            item_copy['summary_method'] = 'failed'
            summarized_items.append(item_copy)
    
    total_time = time.time() - batch_start
    successful = sum(1 for item in summarized_items if item.get('summary_generated', False))
    
    return summarized_items


def main():
    """Main execution function for command-line invocation."""
    import sys
    import json
    
    try:
        # Try to read from stdin first (for pipeline usage), otherwise use file
        news_items = None
        if not sys.stdin.isatty():
            # Reading from stdin (pipeline mode)
            try:
                stdin_data = sys.stdin.read()
                if stdin_data and stdin_data.strip():
                    data = json.loads(stdin_data)
                    news_items = data.get('items', [])
            except (json.JSONDecodeError, ValueError) as e:
                pass
        
        # If stdin didn't work, load from filtered_news.json (pre-filtered top 30)
        if news_items is None:
            # Try filtered_news.json first (guaranteed to be filtered to top 30)
            filtered_file = settings.DATA_DIR / "filtered_news.json"
            input_file = str(filtered_file)
            
            try:
                data = load_json(input_file)
                news_items = data.get('items', [])
            except FileNotFoundError:
                # Fallback to raw_news.json if filtered_news.json doesn't exist
                input_file = settings.RAW_NEWS_FILE
                data = load_json(input_file)
                news_items = data.get('items', [])
        
        if not news_items:
            return 0
        
        # Assign visual tags to articles before summarizing
        news_items = assign_visual_tags_to_articles(news_items)
        
        # Summarize articles
        summarized_items = batch_summarize_news(news_items)
        
        # Extract minimal fields: article_id, title, source_url, summary (needed for video idea generation)
        from app.scripts.data_manager import generate_article_id
        summary_items = []
        for item in summarized_items:
            source_url = item.get('source_url', '')
            article_id = item.get('article_id') or generate_article_id(source_url)
            summary = item.get('summary', '')
            title = item.get('title', '')
            
            summary_items.append({
                'article_id': article_id,
                'title': title,  # Needed for video idea generation
                'source_url': source_url,  # Needed for video idea generation
                'summary': summary,
            })
        
        # Save summaries (minimal format)
        output_file = settings.SUMMARIES_FILE
        output_data = {
            'summarized_at': '',  # Will be set by data_manager
            'total_items': len(summary_items),
            'items': summary_items,
        }
        save_json(output_data, output_file)
        
        return 0
        
    except Exception as e:
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    # Initialize error logging for this script
    from app.scripts.error_logger import initialize_error_logging
    initialize_error_logging()
    
    exit_code = main()
    sys.exit(exit_code)
