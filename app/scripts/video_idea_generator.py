"""
Video idea generator for AI News Tracker.

Generates video ideas from summarized news articles using Hugging Face models.
Focuses on trend potential, virality, and SEO research per competition rules.
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

logger = setup_logger(__name__)

# Video title templates for different formats
VIDEO_TITLE_TEMPLATES = [
    "How {topic} is Changing AI",
    "The Future of {topic} Explained",
    "{topic}: What You Need to Know",
    "Breaking Down {topic}",
    "Understanding {topic} in 2024",
    "{topic} - Complete Guide",
    "Why {topic} Matters for AI",
    "{topic} Explained Simply",
    "The Truth About {topic}",
    "{topic}: A Deep Dive",
]

# Virality factors based on content analysis
VIRALITY_FACTORS = [
    "Timely and trending topic",
    "Practical value for viewers",
    "Industry relevance",
    "Controversial or debated",
    "Novel or breakthrough technology",
    "Real-world applications",
    "Educational content",
    "Comparison or analysis",
]


def extract_key_topics(text: str, max_topics: int = 5) -> List[str]:
    """
    Extract key topics/keywords from text.
    
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
        # Return empty list rather than processing potentially dangerous input
        return []
    
    # Use sanitized text
    text = sanitized_text
    
    # Simple keyword extraction: find capitalized words and important phrases
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
    
    # Find capitalized words (likely proper nouns or important terms)
    capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', text)
    
    # Find multi-word phrases (2-3 words) that might be concepts
    phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b', text)
    
    # Combine and filter
    topics = []
    for word in capitalized_words:
        if word.lower() not in stop_words and word not in topics:
            topics.append(word)
    
    for phrase in phrases:
        if phrase not in topics:
            topics.append(phrase)
    
    # Return top N topics
    return topics[:max_topics]


def generate_video_idea_with_huggingface(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate a video idea using template-based approach with keyword extraction.
    Uses Hugging Face models for text processing and template-based generation.
    
    Note: All articles passed to this function have already been accepted into the feed.
    No filtering should occur here - generate ideas for all accepted articles.
    
    Args:
        item: Article dictionary with title, summary, etc.
        
    Returns:
        Video idea dictionary with trend analysis, SEO keywords, and virality factors
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
            return None
        
        # Extract main topic from sanitized title and summary
        topics = extract_key_topics(sanitized_text, max_topics=5)
        main_topic = topics[0] if topics else "AI Technology"
        
        # Generate video title using template
        video_title_template = random.choice(VIDEO_TITLE_TEMPLATES)
        video_title = video_title_template.format(topic=main_topic)
        
        # Generate video description - create a compelling video concept, not just article summary
        # Use video-focused language and structure
        video_description_parts = []
        
        # Hook/intro
        if any(tag in ['ai startup', 'generative ai', 'llm'] for tag in visual_tags):
            video_description_parts.append(f"Discover how {main_topic} is revolutionizing the AI industry.")
        else:
            video_description_parts.append(f"Explore the cutting-edge developments in {main_topic}.")
        
        # Main content hook
        if "new" in title.lower() or "breakthrough" in summary.lower():
            video_description_parts.append("This breakthrough technology is changing everything we know about AI.")
        elif any(word in title.lower() for word in ['future', 'next', 'coming', 'upcoming']):
            video_description_parts.append("Get an exclusive look at what's coming next in AI technology.")
        else:
            video_description_parts.append("Learn what this means for the future of artificial intelligence.")
        
        # Value proposition
        if "tutorial" in title.lower() or "how" in title.lower():
            video_description_parts.append("This comprehensive guide breaks down everything you need to know.")
        elif "explained" in title.lower() or "understanding" in title.lower():
            video_description_parts.append("We'll explain the key concepts and real-world implications.")
        else:
            video_description_parts.append("We'll dive deep into the technical details and practical applications.")
        
        video_description = " ".join(video_description_parts)
        
        # Generate trend analysis
        trend_analysis = f"This topic represents current developments in {main_topic} with significant potential for engaging video content. "
        if any(tag in ['ai startup', 'generative ai', 'llm', 'large language model'] for tag in visual_tags):
            trend_analysis += "The technology is trending in the AI community and has high search volume."
        else:
            trend_analysis += "The topic has growing interest and practical applications."
        
        # Select virality factors based on content
        selected_factors = random.sample(VIRALITY_FACTORS, min(3, len(VIRALITY_FACTORS)))
        if "breakthrough" in summary.lower() or "new" in title.lower():
            if "Novel or breakthrough technology" not in selected_factors:
                selected_factors[0] = "Novel or breakthrough technology"
        
        # Generate SEO keywords
        target_keywords = topics[:5] if topics else [main_topic]
        # Add common AI/ML keywords for SEO
        seo_keywords = ['AI', 'artificial intelligence', 'machine learning', 'technology']
        for kw in seo_keywords:
            if kw.lower() not in [k.lower() for k in target_keywords]:
                target_keywords.append(kw)
                if len(target_keywords) >= 8:
                    break
        
        # Generate content outline
        content_outline = [
            f"Introduction: Overview of {main_topic} and why it matters",
            f"Main content: Deep dive into key developments and implications",
            "Real-world applications: How this technology is being used",
            "Conclusion: Future outlook and what to watch for"
        ]
        
        # Calculate scores based on content analysis
        trend_score = 0.7 if any(tag in ['ai startup', 'generative ai', 'llm'] for tag in visual_tags) else 0.6
        seo_score = 0.7 if len(target_keywords) >= 5 else 0.5
        uniqueness_score = 0.6 if "new" in title.lower() or "breakthrough" in summary.lower() else 0.5
        engagement_score = (trend_score + seo_score + uniqueness_score) / 3
        
        video_idea = {
            'video_title': video_title,
            'video_description': video_description,
            'trend_analysis': trend_analysis,
            'virality_factors': selected_factors,
            'target_keywords': target_keywords[:8],  # Limit to 8 keywords
            'content_outline': content_outline,
            'target_duration_minutes': 10,
            'estimated_engagement_score': round(engagement_score, 2),
            'trend_score': round(trend_score, 2),
            'seo_score': round(seo_score, 2),
            'uniqueness_score': round(uniqueness_score, 2)
        }
        
        logger.debug(f"Generated video idea: {video_title[:50]}...")
        return video_idea
        
    except Exception as e:
        logger.error(f"Failed to generate video idea: {e}", exc_info=True)
        return None


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
            
            # Generate 1 video idea per article (no multi-part ideas)
            # Note: All articles here have already been accepted into the feed, so generate ideas for all
            num_ideas = 1
            
            for idea_num in range(num_ideas):
                # Generate video idea using Hugging Face (template-based with keyword extraction)
                video_idea_data = generate_video_idea_with_huggingface(item)
                
                if not video_idea_data:
                    logger.error(f"Video idea generation failed for article {i}: {title[:50]}... - No video idea generated")
                    continue
                
                # Format video idea with all generated data (Hugging Face template-based)
                video_idea = {
                    'title': video_idea_data.get('video_title') or video_idea_data.get('title', title),
                    'description': video_idea_data.get('video_description') or video_idea_data.get('description', summary),
                    'source': source,
                    'source_url': source_url,
                    'generated_date': datetime.utcnow().isoformat(),
                    'type': 'video_idea',
                    # Video idea analysis fields (generated with Hugging Face template-based approach)
                    'trend_analysis': video_idea_data.get('trend_analysis', ''),
                    'virality_factors': video_idea_data.get('virality_factors', []),
                    'target_keywords': video_idea_data.get('target_keywords', []),
                    'content_outline': video_idea_data.get('content_outline', []),
                    'target_duration_minutes': video_idea_data.get('target_duration_minutes', 10),
                    'estimated_engagement_score': video_idea_data.get('estimated_engagement_score', 0.5),
                    'trend_score': video_idea_data.get('trend_score', 0.5),
                    'seo_score': video_idea_data.get('seo_score', 0.5),
                    'uniqueness_score': video_idea_data.get('uniqueness_score', 0.5),
                    # Reference to original article
                    'original_title': title,
                    'original_summary': summary,
                }
                
                # Assign visual tags for image generation (categorize if not already present)
                if 'visual_tags' in item and item.get('visual_tags'):
                    video_idea['visual_tags'] = item.get('visual_tags')
                    video_idea['tag_relevance_score'] = item.get('tag_relevance_score', 0)
                else:
                    # Categorize article to get visual tags
                    visual_tags, match_count = categorize_article(item)
                    video_idea['visual_tags'] = visual_tags
                    video_idea['tag_relevance_score'] = match_count
                
                video_ideas.append(video_idea)
                logger.debug(f"Generated idea {idea_num + 1} for article {i}/{len(summaries)}")
            
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

