"""
Article summarization module for AI News Tracker.

Summarizes news articles using llama-cpp-python (local LLM inference).
"""

import re
import html
import json
import os
from typing import List, Dict, Any, Optional
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import assign_visual_tags_to_articles
from app.scripts.input_validator import validate_for_summarization

logger = setup_logger(__name__)

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.error("llama-cpp-python not installed, summarization will fail")

# Global model instance (lazy loading)
_llm_model = None


def get_llm_model() -> Optional['Llama']:
    """
    Get or initialize the LLM model.
    Uses lazy loading to avoid loading model until needed.
    
    Returns:
        Llama model instance or None if unavailable
    """
    global _llm_model
    
    if not LLAMA_AVAILABLE:
        logger.error("llama-cpp-python not available")
        return None
    
    if _llm_model is None:
        model_path = settings.LLM_MODEL_PATH
        
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            logger.error("Please download a GGUF model file and place it in app/models/")
            logger.error("Recommended: Llama 3.2 3B Instruct (Q4_K_M quantization)")
            logger.error("Download from: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF")
            return None
        
        try:
            logger.info(f"Loading LLM model from: {model_path}")
            logger.info(f"Context window: {settings.LLM_N_CTX}, Threads: {settings.LLM_N_THREADS}")
            
            _llm_model = Llama(
                model_path=model_path,
                n_ctx=settings.LLM_N_CTX,
                n_threads=settings.LLM_N_THREADS,
                n_gpu_layers=settings.LLM_N_GPU_LAYERS,
                verbose=False
            )
            
            logger.info("LLM model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}", exc_info=True)
            return None
    
    return _llm_model


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


def summarize_article_with_llm(text: str, max_words: int = None) -> str:
    """
    Summarize a single article using llama-cpp-python.
    
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
    
    # Validate and sanitize input
    is_valid, sanitized_text, reason = validate_for_summarization(text)
    if not is_valid:
        logger.error(f"Input validation failed for summarization: {reason}")
        return ""
    
    # Use sanitized text
    text = sanitized_text
    
    # Get model
    model = get_llm_model()
    if model is None:
        logger.error("LLM model not available for summarization")
        return ""
    
    try:
        # Truncate text if too long (respect context window)
        # Reserve space for prompt and response
        max_input_chars = (settings.LLM_N_CTX * 3) - (max_words * 6)  # Rough estimate
        if len(text) > max_input_chars:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_input_chars} chars")
            text = text[:max_input_chars] + "..."
        
        # Create prompt for summarization
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful AI assistant that summarizes articles concisely and accurately.<|eot_id|><|start_header_id|>user<|end_header_id|>

Summarize the following article in {max_words} words or less. Focus on the key points and main information. Write a clear, concise summary.

Article:
{text}

Summary:<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        logger.debug(f"Generating summary with LLM (input: {len(text)} chars, max_words: {max_words})")
        
        # Generate summary
        response = model(
            prompt,
            max_tokens=max_words * 2,  # Allow some buffer
            temperature=settings.LLM_TEMPERATURE,
            top_p=settings.LLM_TOP_P,
            top_k=settings.LLM_TOP_K,
            stop=["<|eot_id|>", "<|end_of_text|>", "\n\n\n"],
            echo=False
        )
        
        # Extract text from response
        if 'choices' in response and len(response['choices']) > 0:
            summary = response['choices'][0]['text'].strip()
        else:
            logger.error("Unexpected response format from LLM")
            summary = ""
        
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
        logger.error(f"Failed to summarize article with LLM: {e}", exc_info=True)
        # Fallback: return first N words
        words = text.split()[:max_words]
        return " ".join(words)


def summarize_article(text: str, max_words: int = None) -> str:
    """
    Summarize a single article (wrapper for compatibility).
    Uses llama-cpp-python.
    
    Args:
        text: Article text to summarize
        max_words: Maximum words in summary (defaults to settings.SUMMARY_MAX_WORDS)
        
    Returns:
        Summarized text
    """
    return summarize_article_with_llm(text, max_words)


def batch_summarize_news(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Summarize multiple news articles in batch using llama-cpp-python.
    
    Args:
        news_items: List of news item dictionaries with 'title' and 'summary' fields
        
    Returns:
        List of news items with added 'summary' field (if not present or enhanced)
    """
    logger.info(f"Summarizing {len(news_items)} news articles with llama-cpp-python")
    
    # Check LLM availability early
    if not LLAMA_AVAILABLE:
        logger.error("CRITICAL: llama-cpp-python library not available")
        logger.error("Please install: pip install llama-cpp-python")
        logger.error("Then rebuild Docker container: docker-compose build --no-cache python-app")
        raise RuntimeError("llama-cpp-python library not available")
    
    model = get_llm_model()
    if model is None:
        logger.error("CRITICAL: LLM model not available")
        logger.error(f"Model path: {settings.LLM_MODEL_PATH}")
        logger.error("Please download a GGUF model and place it in app/models/")
        raise RuntimeError("LLM model not available")
    
    logger.info(f"Using model: {settings.LLM_MODEL_PATH}")
    
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
                    logger.info(f"Item {i}/{len(news_items)}: Calling LLM for summarization...")
                    summary = summarize_article_with_llm(text_to_summarize)
                    
                    if summary:
                        logger.info(f"Item {i}/{len(news_items)}: Successfully generated summary ({len(summary.split())} words)")
                        successful += 1
                    else:
                        logger.warning(f"Item {i}/{len(news_items)}: Summary generation returned empty string")
                        failed += 1
            
            # Create new item with summary
            summarized_item = item.copy()
            summarized_item['summary'] = summary
            summarized_item['summary_generated'] = bool(summary)
            summarized_item['summary_method'] = 'llama-cpp-python' if summary else 'failed'
            
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
        logger.info("Starting summarization process with llama-cpp-python")
        logger.info("=" * 60)
        
        # Check LLM availability early
        if not LLAMA_AVAILABLE:
            logger.error("CRITICAL: llama-cpp-python library not available")
            logger.error("Please install: pip install llama-cpp-python")
            logger.error("Then rebuild Docker container: docker-compose build --no-cache python-app")
            return 1
        
        model = get_llm_model()
        if model is None:
            logger.error("CRITICAL: LLM model not available")
            logger.error(f"Model path: {settings.LLM_MODEL_PATH}")
            logger.error("Please download a GGUF model and place it in app/models/")
            logger.error("Recommended: Llama 3.2 3B Instruct (Q4_K_M quantization)")
            logger.error("Download from: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF")
            return 1
        
        logger.info(f"Model: {settings.LLM_MODEL_PATH}")
        logger.info(f"Context: {settings.LLM_N_CTX}, Threads: {settings.LLM_N_THREADS}")
        
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
