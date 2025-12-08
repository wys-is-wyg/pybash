"""
Video idea generator for AI News Tracker.

Generates high-value, action-oriented video ideas from summarized news articles.
Focused on AI builders, indie hackers, and AI engineers.
Uses improved prompt structure with automation/builder angles.
"""

import json
import re
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import categorize_article
from app.scripts.input_validator import validate_for_video_ideas
from app.scripts.cache_manager import cached, get_cached, set_cached

logger = setup_logger(__name__)

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
    from llama_cpp.llama_grammar import LlamaGrammar
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    logger.warning("llama-cpp-python not installed, video idea generation will fail")

# Global model instance (shared with summarizer) - cached per process
_llm_model = None


@cached("llm_model", ttl=None, max_size=1)  # Cache LLM model (no expiration, single instance)
def get_llm_model():
    """
    Get or initialize the LLM model (shared instance with caching).
    
    Uses both module-level global cache and decorator cache for maximum efficiency.
    """
    global _llm_model
    
    # Check module-level cache first (fastest)
    if _llm_model is not None:
        return _llm_model
    
    # Check decorator cache
    cached_model = get_cached("llm_model")
    if cached_model is not None:
        _llm_model = cached_model
        return cached_model
    
    if not LLAMA_AVAILABLE:
        return None
    
    import os
    model_path = settings.LLM_MODEL_PATH
    
    if not os.path.exists(model_path):
        logger.error(f"Model file not found: {model_path}")
        return None
    
    try:
        logger.info(f"Loading LLM model for video ideas: {model_path}")
        model = Llama(
            model_path=model_path,
            n_ctx=settings.LLM_N_CTX,
            n_threads=settings.LLM_N_THREADS,
            n_gpu_layers=settings.LLM_N_GPU_LAYERS,
            verbose=False
        )
        
        # Store in both caches
        _llm_model = model
        set_cached("llm_model", model, ttl=None)
        
        logger.info("LLM model loaded successfully for video ideas")
        return model
    except Exception as e:
        logger.error(f"Failed to load LLM model: {e}", exc_info=True)
        return None

# Templates removed - using LLM-generated titles directly

# Automation/builder angles for video ideas
AUTOMATION_ANGLES = [
    "workflow automation",
    "on-device inference",
    "local LLMs",
    "edge AI",
    "API integration",
    "cross-platform tools",
    "privacy-first AI",
    "cost optimization",
    "performance benchmarking",
    "developer tools",
    "model deployment",
    "inference optimization",
]

# Builder-focused value propositions
BUILDER_VALUE_PROPS = [
    "AI builders need to know",
    "changes how AI builders should",
    "impacts AI workflows",
    "opens opportunities for indie hackers",
    "affects AI engineers building",
    "matters for people who make AI tools",
    "shifts the AI landscape",
]

# Example workflow templates
WORKFLOW_TEMPLATES = [
    "Show how to {action} using {tool} to {outcome}",
    "Demonstrate {workflow} that {benefit}",
    "Build a {type} workflow that {function}",
    "Compare {option1} vs {option2} for {use_case}",
    "Create a {tool} that {action}",
    "Implement {feature} using {technology}",
    "Set up {system} to {achieve}",
]


def extract_key_topics(text: str, max_topics: int = 5) -> List[str]:
    """
    Extract key topics/keywords from text, prioritizing entities, companies, and AI/tech terms.
    
    Args:
        text: Text to analyze
        max_topics: Maximum number of topics to extract
        
    Returns:
        List of key topics/keywords
    """
    if not text:
        return []
    
    # Validate and sanitize input before processing
    is_valid, sanitized_text, reason = validate_for_video_ideas(text)
    if not is_valid:
        logger.warning(f"Input validation failed for topic extraction: {reason}")
        return []
    
    # Use sanitized text
    text = sanitized_text
    
    # Common sentence starters and non-entity words to exclude
    excluded_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'sometimes', 'after', 'before', 'during', 'while', 'when', 'where', 'why', 'how', 'what', 'which',
        'who', 'whom', 'whose', 'if', 'then', 'else', 'because', 'since', 'until', 'unless', 'although',
        'however', 'therefore', 'moreover', 'furthermore', 'nevertheless', 'meanwhile', 'additionally',
        'creator', 'creators', 'creates', 'created', 'creating', 'creation'
    }
    
    # Known AI/tech companies and entities (prioritize these)
    known_entities = {
        'openai', 'deepmind', 'anthropic', 'google', 'microsoft', 'meta', 'facebook', 'amazon', 'aws',
        'nvidia', 'intel', 'amd', 'tesla', 'spacex', 'apple', 'ibm', 'oracle', 'salesforce', 'palantir',
        'elon musk', 'sam altman', 'sundar pichai', 'satya nadella', 'mark zuckerberg', 'jeff bezos',
        'jensen huang', 'tim cook', 'larry page', 'sergey brin', 'bill gates', 'steve jobs',
        'gpt', 'claude', 'gemini', 'llama', 'mistral', 'copilot', 'chatgpt', 'bard', 'sora', 'dall-e',
        'transformer', 'bert', 'gpt-3', 'gpt-4', 'gpt-5', 'claude-3', 'claude-4', 'palm', 'palm-2',
        'neuralink', 'waymo', 'cruise', 'arize', 'hugging face', 'stability ai', 'midjourney',
        'mad men'  # Example: TV show that might appear in AI context
    }
    
    topics = []
    seen_lower = set()
    
    # First, find multi-word entities (2-3 words) - these are most likely to be real entities
    # Pattern: Capitalized word + (optional capitalized word) + (optional capitalized word)
    multi_word_entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b', text)
    for entity in multi_word_entities:
        entity_lower = entity.lower()
        if entity_lower not in seen_lower and entity_lower not in excluded_words:
            # Check if it contains known entity keywords or looks like a proper entity
            if any(known in entity_lower for known in known_entities) or len(entity.split()) >= 2:
                topics.append(entity)
                seen_lower.add(entity_lower)
    
    # Find single capitalized words, but prioritize known entities and filter out common words
    single_words = re.findall(r'\b([A-Z][a-z]+)\b', text)
    
    # Known AI/tech terms (single words)
    ai_tech_terms = {
        'ai', 'ml', 'llm', 'nlp', 'cv', 'gan', 'rnn', 'cnn', 'transformer', 'bert', 'gpt', 'claude',
        'neural', 'deep', 'learning', 'algorithm', 'model', 'dataset', 'training', 'inference',
        'robotics', 'automation', 'autonomous', 'quantum', 'blockchain', 'crypto', 'web3'
    }
    
    for word in single_words:
        word_lower = word.lower()
        if word_lower not in seen_lower and word_lower not in excluded_words:
            # Prioritize known entities and AI/tech terms
            if word_lower in known_entities or word_lower in ai_tech_terms:
                topics.append(word)
                seen_lower.add(word_lower)
            # Only add other capitalized words if they appear multiple times (likely important)
            elif text.count(word) >= 2:
                topics.append(word)
                seen_lower.add(word_lower)
    
    # Also look for known entity patterns in lowercase (e.g., "DeepMind" might appear as "deepmind")
    text_lower = text.lower()
    for entity in known_entities:
        if entity in text_lower and entity not in seen_lower:
            # Capitalize properly
            entity_title = ' '.join(word.capitalize() for word in entity.split())
            topics.append(entity_title)
            seen_lower.add(entity)
    
    # Return top N topics, prioritizing multi-word entities
    # Sort: multi-word first, then known entities, then others
    def topic_priority(topic):
        topic_lower = topic.lower()
        if len(topic.split()) > 1:
            return 0  # Multi-word entities first
        elif topic_lower in known_entities or topic_lower in ai_tech_terms:
            return 1  # Known entities second
        else:
            return 2  # Others last
    
    topics_sorted = sorted(topics, key=topic_priority)
    return topics_sorted[:max_topics]


def extract_automation_angle(title: str, summary: str) -> str:
    """
    Extract automation/builder angle from article content.
    
    Args:
        title: Article title
        summary: Article summary
        
    Returns:
        AI angle string
    """
    text_lower = f"{title} {summary}".lower()
    
    # Check for specific automation-related terms
    if any(term in text_lower for term in ['api', 'sdk', 'developer', 'tool', 'platform']):
        return "API integration"
    elif any(term in text_lower for term in ['local', 'on-device', 'edge', 'offline']):
        return "edge AI"
    elif any(term in text_lower for term in ['privacy', 'secure', 'encrypted']):
        return "privacy-first AI"
    elif any(term in text_lower for term in ['cost', 'price', 'cheap', 'affordable']):
        return "cost optimization"
    elif any(term in text_lower for term in ['speed', 'performance', 'fast', 'benchmark']):
        return "performance benchmarking"
    elif any(term in text_lower for term in ['deploy', 'production', 'infrastructure']):
        return "model deployment"
    else:
        return random.choice(AUTOMATION_ANGLES)


# Define JSON schema for video ideas array (for llama grammar)
VIDEO_IDEA_ARRAY_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "concept_summary": {"type": "string"},
            "why_matters_builders": {"type": "string"},
            "example_workflow": {"type": "string"},
            "predicted_impact": {"type": "string"}
        },
        "required": ["title", "concept_summary"]
    }
}


def generate_batch_video_ideas_with_llm(
    item: Dict[str, Any],
    num_ideas: int = 2,
    angle_variations: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate multiple video ideas in a single LLM call using grammar-enforced JSON array.
    
    Args:
        item: Article dictionary with title, summary, etc.
        num_ideas: Number of video ideas to generate
        angle_variations: List of different angles/focuses to consider for variety
        
    Returns:
        List of video idea dictionaries
    """
    model = get_llm_model()
    if model is None:
        return []
    
    try:
        title = item.get('title', '')
        summary = item.get('summary', '')
        visual_tags = item.get('visual_tags', [])
        
        # Validate input
        combined_text = f"{title} {summary}"
        is_valid, sanitized_text, reason = validate_for_video_ideas(combined_text)
        if not is_valid:
            logger.warning(f"Input validation failed: {reason}")
            return []
        
        # Extract topics and AI angle for context
        topics = extract_key_topics(sanitized_text, max_topics=5)
        main_topic = topics[0] if topics else "AI Technology"
        automation_angle = extract_automation_angle(title, summary)
        
        # Use provided angle variations or generate default ones
        if angle_variations is None:
            text_lower = sanitized_text.lower()
            is_breakthrough = any(word in text_lower for word in ['breakthrough', 'revolutionary', 'game-changer'])
            is_announcement = any(word in text_lower for word in ['announces', 'unveils', 'launches', 'releases'])
            
            angle_variations = []
            if num_ideas >= 1:
                angle_variations.append("immediate practical implications for AI builders")
            if num_ideas >= 2:
                angle_variations.append("hidden opportunities and workflow automation potential")
            if num_ideas >= 3:
                angle_variations.append(f"{automation_angle} applications")
            if num_ideas >= 4:
                angle_variations.append("long-term strategic impact for indie hackers")
        
        # Create grammar from schema
        try:
            grammar = LlamaGrammar.from_json_schema(json.dumps(VIDEO_IDEA_ARRAY_SCHEMA))
        except Exception as e:
            logger.error(f"Grammar creation failed: {e}")
            return []
        
        # Build prompt requesting multiple ideas with different angles
        angles_text = "\n".join([f"- {angle}" for angle in angle_variations[:num_ideas]])
        topics_str = ", ".join(topics[:3]) if topics else "AI technology"
        
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a JSON generator. Return ONLY a valid JSON array, no explanatory text.<|eot_id|><|start_header_id|>user<|end_header_id|>

Article: {title}
Summary: {summary[:400]}
Topics: {topics_str}
Automation Angle: {automation_angle}

Generate {num_ideas} different video ideas as a JSON array. Consider these angles:
{angles_text}

Each idea should have:
- title: Hook title for AI builders
- concept_summary: 2-3 sentence video concept
- why_matters_builders: Why this matters for builders
- example_workflow: Example use case
- predicted_impact: One sentence prediction

Return ONLY the JSON array, no other text.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        # Generate with LLM using grammar
        logger.debug(f"Generating {num_ideas} video ideas in batch with LLM...")
        import signal
        import time
        
        timeout_seconds = settings.LLM_GENERATION_TIMEOUT
        
        def timeout_handler(signum, frame):
            raise TimeoutError("LLM generation timed out")
        
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
        except (AttributeError, OSError):
            pass
        
        try:
            start_time = time.time()
            response = model(
                prompt,
                max_tokens=800,  # Increased for multiple ideas
                grammar=grammar,  # Enforce JSON array format
                temperature=0.6,  # Slightly higher for variety
                top_p=0.9,
                top_k=40,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                echo=False
            )
            elapsed = time.time() - start_time
            logger.debug(f"LLM batch generation completed in {elapsed:.1f}s")
        except TimeoutError:
            logger.warning(f"LLM generation timed out after {timeout_seconds}s")
            return []
        finally:
            try:
                signal.alarm(0)
            except (AttributeError, OSError):
                pass
        
        # Parse response (grammar ensures it's valid JSON array)
        if 'choices' in response and len(response['choices']) > 0:
            response_text = response['choices'][0]['text'].strip()
            try:
                ideas = json.loads(response_text)
                if isinstance(ideas, list):
                    logger.debug(f"Successfully parsed {len(ideas)} ideas from LLM response")
                    return ideas
                else:
                    logger.warning("LLM returned non-array, wrapping in list")
                    return [ideas] if isinstance(ideas, dict) else []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM response: {e}")
                logger.debug(f"Response text: {response_text[:200]}")
                return []
        else:
            logger.error("Unexpected response format from LLM")
            return []
            
    except Exception as e:
        logger.error(f"Error during batch LLM generation: {e}", exc_info=True)
        return []


# Old single-idea function removed - using batch generation instead

def generate_video_ideas_for_article(item: Dict[str, Any], num_ideas: int = 2) -> List[Dict[str, Any]]:
    """
    Generate multiple high-value video ideas from a single article.
    Uses improved prompt structure focused on AI builders.
    
    Note: All articles passed to this function have already been accepted into the feed.
    No filtering should occur here - generate ideas for all accepted articles.
    
    Args:
        item: Article dictionary with title, summary, etc.
        num_ideas: Number of video ideas to generate (3-5)
        
    Returns:
        List of video idea dictionaries with structured format
    """
    try:
        title = item.get('title', '')
        summary = item.get('summary', '')
        source = item.get('source', '')
        visual_tags = item.get('visual_tags', [])
        
        # Validate title and summary before processing
        combined_text = f"{title} {summary}"
        is_valid, sanitized_text, reason = validate_for_video_ideas(combined_text)
        if not is_valid:
            logger.warning(f"Input validation failed for video idea generation: {reason}")
            return []
        
        # Extract main topic and AI angle
        topics = extract_key_topics(sanitized_text, max_topics=5)
        main_topic = topics[0] if topics else "AI Technology"
        automation_angle = extract_automation_angle(title, summary)
        
        # Analyze article for key insights
        text_lower = sanitized_text.lower()
        is_breakthrough = any(word in text_lower for word in ['breakthrough', 'revolutionary', 'game-changer'])
        is_announcement = any(word in text_lower for word in ['announces', 'unveils', 'launches', 'releases'])
        is_exec_change = any(word in text_lower for word in ['executive', 'ceo', 'leaves', 'departs', 'resigns'])
        is_strategy_shift = any(word in text_lower for word in ['strategy', 'pivot', 'shift', 'change', 'new direction'])
        
        # Generate all ideas in a single batch LLM call
        logger.info(f"Generating {num_ideas} video ideas for: {title[:50]}...")
        raw_ideas = generate_batch_video_ideas_with_llm(item, num_ideas=num_ideas)
        
        if not raw_ideas:
            logger.warning(f"No video ideas generated for: {title[:50]}...")
            return []
        
        # Process and format the ideas - minimal output only
        processed_ideas = []
        
        for idea_data in raw_ideas:
            if not isinstance(idea_data, dict) or not idea_data.get('title'):
                continue
            
            # Minimal output: just title and description from LLM (no redundant fields)
            processed_ideas.append({
                'video_title': idea_data.get('title', '').strip(),
                'video_description': idea_data.get('concept_summary', '').strip(),  # Just LLM's concept_summary
            })
        
        logger.debug(f"Generated {len(processed_ideas)} video ideas for: {title[:50]}...")
        return processed_ideas
        
    except Exception as e:
        logger.error(f"Failed to generate video ideas: {e}", exc_info=True)
        return []


def generate_video_idea_with_huggingface(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate a single video idea (backward compatibility).
    Now uses improved prompt structure.
    
    Args:
        item: Article dictionary with title, summary, etc.
        
    Returns:
        Video idea dictionary (first idea from generate_video_ideas_for_article)
    """
    ideas = generate_video_ideas_for_article(item, num_ideas=1)
    return ideas[0] if ideas else None


def format_video_idea(title: str, description: str, source: str, source_url: str = "") -> Dict[str, Any]:
    """
    Format a video idea into structured dictionary.
    
    Args:
        title: Video title
        description: Video description
        source: Source name
        source_url: Source URL
        
    Returns:
        Formatted video idea dictionary
    """
    return {
        'title': title,
        'description': description,
        'source': source,
        'source_url': source_url,
        'generated_date': datetime.utcnow().isoformat(),
        'type': 'video_idea',
    }


def generate_video_ideas(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate video ideas from summarized articles.
    
    Args:
        summaries: List of summarized news item dictionaries
        
    Returns:
        List of video idea dictionaries
    """
    logger.info(f"Generating video ideas from {len(summaries)} summaries")
    
    video_ideas = []
    max_ideas_per_article = settings.MAX_VIDEO_IDEAS_PER_ARTICLE
    
    for i, item in enumerate(summaries, 1):
        try:
            title = item.get('title', '')
            summary = item.get('summary', '')
            source = item.get('source', '')
            source_url = item.get('source_url', '')
            
            # Generate 3-5 video ideas per article with improved structure
            # Note: All articles here have already been accepted into the feed, so generate ideas for all
            num_ideas = 2
            
            # Generate multiple video ideas with improved prompt structure
            video_ideas_data = generate_video_ideas_for_article(item, num_ideas=num_ideas)
                
            if not video_ideas_data:
                logger.error(f"Video idea generation failed for article {i}: {title[:50]}... - No video ideas generated")
                continue
            
            # Get article_id from item or generate it
            from app.scripts.data_manager import generate_article_id
            article_id = item.get('article_id') or generate_article_id(source_url)
            
            # Format each video idea (clean format: just article_id, LLM title, LLM description)
            for idea_num, video_idea_data in enumerate(video_ideas_data):
                # Extract LLM's actual title and description (just what LLM returns)
                video_title = video_idea_data.get('video_title', '')
                video_description = video_idea_data.get('video_description', '')  # LLM's concept_summary
                
                video_idea = {
                    'article_id': article_id,
                    'video_title': video_title,
                    'video_description': video_description,
                }
                
                video_ideas.append(video_idea)
                logger.debug(f"Generated idea {idea_num + 1}/{num_ideas} for article {i}/{len(summaries)}")
            
        except Exception as e:
            logger.error(f"Failed to generate video idea for item {i}/{len(summaries)}: {e}")
            continue
    
    logger.info(f"Successfully generated {len(video_ideas)} video ideas")
    return video_ideas


def main():
    """Main execution function for command-line invocation."""
    import sys
    import json
    
    try:
        logger.info("Starting video idea generation process")
        
        # Try to read from stdin first (for pipeline usage), otherwise use file
        summaries = None
        if not sys.stdin.isatty():
            # Reading from stdin (pipeline mode)
            logger.info("Reading summaries from stdin")
            try:
                stdin_data = sys.stdin.read()
                if stdin_data and stdin_data.strip():
                    data = json.loads(stdin_data)
                    summaries = data.get('items', [])
                    logger.info(f"Loaded {len(summaries)} summaries from stdin")
                else:
                    logger.warning("stdin is empty, falling back to file")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON from stdin: {e}")
                logger.info("Falling back to file input")
        
        # If stdin didn't work, load from file
        if summaries is None:
            input_file = settings.SUMMARIES_FILE
            logger.info(f"Loading summaries from {input_file}")
            
            try:
                data = load_json(input_file)
                summaries = data.get('items', [])
                logger.info(f"Loaded {len(summaries)} summaries from file")
            except FileNotFoundError:
                logger.error(f"Input file not found: {input_file}")
                return 1
        
        if not summaries:
            logger.warning("No summaries to process")
            return 0
        
        # Safety check: Limit to top 30 summaries if more than expected
        EXPECTED_MAX_SUMMARIES = 30
        if len(summaries) > EXPECTED_MAX_SUMMARIES:
            logger.warning(f"Found {len(summaries)} summaries, but expected max {EXPECTED_MAX_SUMMARIES}. Limiting to top {EXPECTED_MAX_SUMMARIES}.")
            # Keep top 30 (they should already be sorted by relevance from pre-filter)
            summaries = summaries[:EXPECTED_MAX_SUMMARIES]
            logger.info(f"Limited to {len(summaries)} summaries for processing")
        
        # Generate video ideas
        video_ideas = generate_video_ideas(summaries)
        
        # Save video ideas
        output_file = settings.VIDEO_IDEAS_FILE
        output_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_ideas': len(video_ideas),
            'items': video_ideas,
        }
        save_json(output_data, output_file)
        
        logger.info("Video idea generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Video idea generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)
