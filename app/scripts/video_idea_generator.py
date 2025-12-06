"""
Video idea generator for AI News Tracker.

Generates video ideas from summarized news articles using template-based approach.
"""

import re
from typing import List, Dict, Any
from datetime import datetime
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json
from app.scripts.tag_categorizer import categorize_article

logger = setup_logger(__name__)


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


def generate_video_title(summary: str, title: str = "") -> str:
    """
    Generate a video title from article summary and title.
    
    Args:
        summary: Article summary text
        title: Original article title
        
    Returns:
        Generated video title
    """
    # Extract key topics
    topics = extract_key_topics(summary or title, max_topics=3)
    
    # Video title templates
    templates = [
        "How {topic} is Changing AI",
        "Breaking Down {topic}",
        "The Future of {topic}",
        "Understanding {topic}",
        "{topic}: What You Need to Know",
        "Exploring {topic}",
        "{topic} Explained",
    ]
    
    # Use first available topic
    if topics:
        topic = topics[0]
        import random
        template = random.choice(templates)
        video_title = template.format(topic=topic)
    else:
        # Fallback: use original title with prefix
        if title:
            video_title = f"AI News: {title[:60]}"
        else:
            video_title = "AI News Update"
    
    return video_title


def generate_video_description(summary: str, source: str = "") -> str:
    """
    Generate video description from summary.
    
    Args:
        summary: Article summary
        source: Source name
        
    Returns:
        Generated video description
    """
    if not summary:
        return "Watch this video to learn more about the latest developments in AI."
    
    # Create description from summary
    description = summary.strip()
    
    # Add source attribution if available
    if source:
        description += f"\n\nSource: {source}"
    
    # Add call to action
    description += "\n\nStay updated with the latest AI news and insights."
    
    return description


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
            
            # Generate 1-3 video ideas per article
            num_ideas = min(max_ideas_per_article, 3)
            
            for idea_num in range(num_ideas):
                # Generate video title
                video_title = generate_video_title(summary, title)
                
                # Add variation for multiple ideas from same article
                if idea_num > 0:
                    video_title = f"{video_title} (Part {idea_num + 1})"
                
                # Generate description
                video_description = generate_video_description(summary, source)
                
                # Format video idea
                video_idea = format_video_idea(
                    title=video_title,
                    description=video_description,
                    source=source,
                    source_url=source_url
                )
                
                # Add reference to original article and preserve tags
                video_idea['original_title'] = title
                video_idea['original_summary'] = summary
                video_idea['tags'] = item.get('tags', [])  # Preserve RSS tags
                # Assign visual tags for image generation (categorize if not already present)
                if 'visual_tags' in item and item.get('visual_tags'):
                    video_idea['visual_tags'] = item.get('visual_tags')
                    video_idea['tag_relevance_score'] = item.get('tag_relevance_score', 0)
                else:
                    # Categorize article to get visual tags
                    visual_tags, score = categorize_article(item)
                    video_idea['visual_tags'] = visual_tags
                    video_idea['tag_relevance_score'] = score
                
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
    
    try:
        logger.info("Starting video idea generation process")
        
        # Load summaries from file
        input_file = settings.SUMMARIES_FILE
        logger.info(f"Loading summaries from {input_file}")
        
        try:
            data = load_json(input_file)
            summaries = data.get('items', [])
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

