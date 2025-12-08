"""
Article summarization module for AI News Tracker.

Summarizes news articles using Google AI Studio (Gemini).
"""

import re
import html
import json
import time
from typing import List, Dict, Any, Optional
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles
from app.scripts.input_validator import validate_for_summarization

logger = setup_logger(__name__)

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    if settings.GOOGLE_AI_API_KEY:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        logger.info("Google AI Studio (Gemini) configured for summarization")
    else:
        GEMINI_AVAILABLE = False
        logger.warning("GOOGLE_AI_API_KEY not set, summarization will fail")
except ImportError:
    GEMINI_AVAILABLE = False
    logger.error("google-generativeai not installed, summarization will fail")


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


def summarize_article_with_gemini(text: str, max_words: int = None) -> str:
    """
    Summarize a single article using Gemini API.
    
    Args:
        text: Article text to summarize
        max_words: Maximum words in summary (defaults to settings.SUMMARY_MAX_WORDS)
        
    Returns:
        Summarized text
    """
    if not GEMINI_AVAILABLE or not settings.GOOGLE_AI_API_KEY:
        logger.error("Gemini not available for summarization")
        return ""
    
    if max_words is None:
        max_words = settings.SUMMARY_MAX_WORDS
    
    if not text or len(text.strip()) == 0:
        logger.warning("Empty text provided for summarization")
        return ""
    
    # Validate and sanitize input
    is_valid, sanitized_text, reason = validate_for_summarization(text)
    if not is_valid:
        logger.error(f"Input validation failed for summarization: {reason}")
        return ""
    
    # Use sanitized text
    text = sanitized_text
    
    try:
        # Truncate text if too long (Gemini has token limits)
        # Rough estimate: 1 token ≈ 4 characters, max ~1M tokens for gemini-1.5-flash
        # But we'll limit to ~50K characters to be safe and faster
        max_chars = 50000
        if len(text) > max_chars:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars} chars")
            text = text[:max_chars] + "..."
        
        # Create prompt for Gemini
        prompt = f"""Summarize the following article in {max_words} words or less. Focus on the key points and main information. Write a clear, concise summary.

Article:
{text}

Summary:"""
        
        # Generate summary with Gemini
        logger.debug(f"Calling Gemini API with model: {settings.GOOGLE_AI_MODEL}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        try:
            model = genai.GenerativeModel(settings.GOOGLE_AI_MODEL)
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for more factual summaries
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": max_words * 2,  # Allow some buffer
                }
            )
            
            # Check if response has text
            if not response.text:
                logger.error("Gemini API returned empty response")
                raise ValueError("Empty response from Gemini API")
            
            summary = response.text.strip()
            logger.debug(f"Received response from Gemini ({len(summary)} characters)")
            
        except Exception as api_error:
            logger.error(f"Gemini API call failed: {api_error}", exc_info=True)
            # Re-raise to be caught by outer exception handler
            raise
        
        # Clean HTML tags and entities from summary
        summary = clean_html_and_entities(summary)
        
        # Ensure summary doesn't exceed max_words
        words = summary.split()
        if len(words) > max_words:
            summary = " ".join(words[:max_words])
            logger.debug(f"Truncated summary from {len(words)} to {max_words} words")
        
        logger.debug(f"Generated summary ({len(summary.split())} words)")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize article with Gemini: {e}", exc_info=True)
        # Fallback: return first N words
        words = text.split()[:max_words]
        return " ".join(words)


def summarize_article(text: str, max_words: int = None) -> str:
    """
    Summarize a single article (wrapper for compatibility).
    Uses Gemini API.
    
    Args:
        text: Article text to summarize
        max_words: Maximum words in summary (defaults to settings.SUMMARY_MAX_WORDS)
        
    Returns:
        Summarized text
    """
    return summarize_article_with_gemini(text, max_words)


def batch_summarize_news(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Summarize multiple news articles in batch using Gemini API.
    
    Args:
        news_items: List of news item dictionaries with 'title' and 'summary' fields
        
    Returns:
        List of news items with added 'summary' field (if not present or enhanced)
    """
    logger.info(f"Summarizing {len(news_items)} news articles with Gemini")
    
    # Check Gemini availability with detailed logging
    if not GEMINI_AVAILABLE:
        logger.error("Gemini library not available - google-generativeai not installed")
        logger.error("Please install: pip install google-generativeai")
        raise RuntimeError("Gemini library not available")
    
    if not settings.GOOGLE_AI_API_KEY:
        logger.error("GOOGLE_AI_API_KEY not set in environment variables")
        logger.error("Please set GOOGLE_AI_API_KEY in .env file")
        raise RuntimeError("GOOGLE_AI_API_KEY not configured")
    
    logger.info(f"Using Gemini model: {settings.GOOGLE_AI_MODEL}")
    logger.info(f"API key configured: {settings.GOOGLE_AI_API_KEY[:10]}...")
    
    summarized_items = []
    successful = 0
    failed = 0
    
    for i, item in enumerate(news_items, 1):
        try:
            # Combine title and summary for better context
            title = item.get('title', '')
            existing_summary = item.get('summary', '')
            
            logger.info(f"Processing item {i}/{len(news_items)}: {title[:50]}...")
            
            # Use existing summary if it's already good, otherwise summarize
            if existing_summary and len(existing_summary.split()) >= settings.SUMMARY_MIN_WORDS:
                summary = clean_html_and_entities(existing_summary)
                logger.info(f"Item {i}/{len(news_items)}: Using existing summary (cleaned)")
            else:
                # Combine title and summary for full context
                text_to_summarize = f"{title}. {existing_summary}" if existing_summary else title
                
                if not text_to_summarize.strip():
                    logger.warning(f"Item {i}/{len(news_items)}: No text to summarize")
                    summary = ""
                else:
                    logger.info(f"Item {i}/{len(news_items)}: Calling Gemini API for summarization...")
                    summary = summarize_article_with_gemini(text_to_summarize)
                    
                    if summary:
                        logger.info(f"Item {i}/{len(news_items)}: Successfully generated summary ({len(summary.split())} words)")
                        successful += 1
                    else:
                        logger.warning(f"Item {i}/{len(news_items)}: Summary generation returned empty string")
                        failed += 1
                    
                    # Add small delay to avoid rate limiting (Gemini free tier: 15 req/min)
                    if i < len(news_items):
                        logger.debug(f"Waiting 4 seconds before next request (rate limiting)...")
                        time.sleep(4)  # ~15 requests per minute max
            
            # Create new item with summary
            summarized_item = item.copy()
            summarized_item['summary'] = summary
            summarized_item['summary_generated'] = bool(summary)
            summarized_item['summary_method'] = 'gemini' if summary else 'failed'
            
            summarized_items.append(summarized_item)
            
        except Exception as e:
            logger.error(f"Failed to summarize item {i}/{len(news_items)}: {e}", exc_info=True)
            failed += 1
            # Keep original item without summary
            item_copy = item.copy()
            item_copy['summary'] = item.get('summary', '')
            item_copy['summary_generated'] = False
            item_copy['summary_method'] = 'failed'
            summarized_items.append(item_copy)
    
    logger.info(f"Summarization complete: {successful} successful, {failed} failed out of {len(news_items)} total")
    
    if failed > 0:
        logger.warning(f"{failed} articles failed to summarize - check logs for details")
    
    return summarized_items


def main():
    """Main execution function for command-line invocation."""
    import sys
    
    try:
        logger.info("=" * 60)
        logger.info("Starting summarization process with Gemini")
        logger.info("=" * 60)
        
        # Check Gemini availability early
        if not GEMINI_AVAILABLE:
            logger.error("CRITICAL: Gemini library not available")
            logger.error("Please install: pip install google-generativeai")
            logger.error("Then rebuild Docker container: docker-compose build --no-cache python-app")
            return 1
        
        if not settings.GOOGLE_AI_API_KEY:
            logger.error("CRITICAL: GOOGLE_AI_API_KEY not set")
            logger.error("Please add GOOGLE_AI_API_KEY to .env file")
            return 1
        
        logger.info(f"Gemini model: {settings.GOOGLE_AI_MODEL}")
        logger.info(f"API key: {settings.GOOGLE_AI_API_KEY[:10]}...{settings.GOOGLE_AI_API_KEY[-4:]}")
        
        # Load raw news from file or stdin
        news_items = None
        
        # Try stdin first (for pipeline usage)
        if not sys.stdin.isatty():
            logger.info("Reading news items from stdin...")
            try:
                stdin_data = sys.stdin.read()
                logger.debug(f"Read {len(stdin_data)} characters from stdin")
                if stdin_data and stdin_data.strip():
                    data = json.loads(stdin_data)
                    news_items = data.get('items', [])
                    logger.info(f"Loaded {len(news_items)} news items from stdin")
                else:
                    logger.warning("stdin is empty")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON from stdin: {e}")
                logger.info("Falling back to file input")
        
        # If stdin didn't work, load from file
        if news_items is None:
            input_file = settings.RAW_NEWS_FILE
            logger.info(f"Loading news items from file: {input_file}")
            
            try:
                data = load_json(input_file)
                news_items = data.get('items', [])
                logger.info(f"Loaded {len(news_items)} news items from file")
            except FileNotFoundError:
                logger.error(f"Input file not found: {input_file}")
                logger.error("Please ensure RSS scraper has run first")
                return 1
            except Exception as e:
                logger.error(f"Failed to load input file: {e}", exc_info=True)
                return 1
        
        if not news_items:
            logger.warning("No news items to summarize")
            return 0
        
        logger.info(f"Processing {len(news_items)} articles...")
        
        # Assign visual tags to articles before summarizing
        logger.info("Assigning visual tags to articles...")
        try:
            news_items = assign_visual_tags_to_articles(news_items)
            logger.info("Visual tags assigned successfully")
        except Exception as e:
            logger.warning(f"Failed to assign visual tags: {e}, continuing without tags")
        
        # Summarize articles
        logger.info("Starting batch summarization...")
        try:
            summarized_items = batch_summarize_news(news_items)
            logger.info(f"Summarization complete: {len(summarized_items)} items processed")
        except RuntimeError as e:
            logger.error(f"Summarization failed with configuration error: {e}")
            return 1
        except Exception as e:
            logger.error(f"Summarization failed unexpectedly: {e}", exc_info=True)
            return 1
        
        # Save summaries
        output_file = settings.SUMMARIES_FILE
        logger.info(f"Saving summaries to: {output_file}")
        try:
            output_data = {
                'summarized_at': '',  # Will be set by data_manager
                'total_items': len(summarized_items),
                'items': summarized_items,
            }
            save_json(output_data, output_file)
            logger.info(f"Summaries saved successfully to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save summaries: {e}", exc_info=True)
            return 1
        
        logger.info("=" * 60)
        logger.info("Summarization completed successfully")
        logger.info("=" * 60)
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Summarization interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Summarization failed with unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)
