"""
Video idea generator for AI News Tracker.

Generates high-value, action-oriented video ideas from summarized news articles.
Focused on automation builders, indie hackers, and AI engineers.
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

logger = setup_logger(__name__)

# Improved video title templates - action-oriented with hooks
VIDEO_TITLE_TEMPLATES = [
    "{topic}: What {change} *REALLY* Means for Builders",
    "The Hidden {angle} Behind {topic} (Why Builders Should Care)",
    "Should AI Builders Bet on {topic}? {insight} Suggests {answer}",
    "{topic} Shake-Up: What {event} *Really* Means for Automation",
    "The {angle} Battle: How {topic} Shifts the Future of {focus}",
    "{topic} for Builders: {opportunity} You Can't Ignore",
    "Why {topic} Changes Everything for {audience} (And What to Do)",
    "{topic} Deep Dive: {action} Workflows You Can Build Today",
    "The {angle} Behind {topic}: {prediction} for Automation",
    "{topic} Explained: {insight} That Changes How We Build",
]

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
    "automation builders need to know",
    "changes how automation builders should",
    "impacts automation workflows",
    "opens opportunities for indie hackers",
    "affects AI engineers building",
    "matters for people who make AI tools",
    "shifts the automation landscape",
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
        Automation angle string
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


def generate_video_ideas_for_article(item: Dict[str, Any], num_ideas: int = 1) -> List[Dict[str, Any]]:
    """
    Generate a single simplified video idea from an article.
    Simplified for faster processing.
    
    Args:
        item: Article dictionary with title, summary, etc.
        num_ideas: Number of video ideas to generate (always 1 for speed)
        
    Returns:
        List with single video idea dictionary
    """
    try:
        title = item.get('title', '')
        summary = item.get('summary', '')
        visual_tags = item.get('visual_tags', [])
        
        # Validate title and summary
        combined_text = f"{title} {summary}"
        is_valid, sanitized_text, reason = validate_for_video_ideas(combined_text)
        if not is_valid:
            logger.warning(f"Input validation failed: {reason}")
            return []
        
        # Extract main topic (simplified - just use first few words of title)
        topics = extract_key_topics(sanitized_text, max_topics=3)
        main_topic = topics[0] if topics else title.split()[0] if title else "AI Technology"
        
        # Simple title generation
        title_templates = [
            f"{main_topic}: What Builders Need to Know",
            f"{main_topic} - Automation Builder's Guide",
            f"How {main_topic} Changes Automation",
        ]
        video_title = title_templates[hash(title) % len(title_templates)]
        
        # Simple description
        video_description = f"{main_topic} represents an important development for automation builders. {summary[:200]} This has practical implications for building AI-powered workflows and automation tools."
        
        # Simple trend analysis
        trend_analysis = f"Current development in {main_topic} with relevance for automation builders."
        
        # Simple keywords
        target_keywords = topics[:5] if topics else [main_topic]
        target_keywords.extend(["automation", "AI builders"])
        target_keywords = list(dict.fromkeys(target_keywords))[:6]
        
        # Simple scores
        trend_score = 0.6
        seo_score = 0.6
        uniqueness_score = 0.6
        engagement_score = 0.6
        
        video_idea = {
            'video_title': video_title,
            'video_description': video_description,
            'trend_analysis': trend_analysis,
            'virality_factors': ["Practical value for automation builders"],
            'target_keywords': target_keywords,
            'content_outline': [
                f"Introduction: {main_topic} overview",
                f"Main content: Practical implications",
                "Conclusion: Actionable takeaways"
            ],
            'target_duration_minutes': 10,
            'estimated_engagement_score': round(engagement_score, 2),
            'trend_score': round(trend_score, 2),
            'seo_score': round(seo_score, 2),
            'uniqueness_score': round(uniqueness_score, 2),
        }
        
        return [video_idea]
        
    except Exception as e:
        logger.error(f"Failed to generate video idea: {e}", exc_info=True)
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
        
        # Generate video description - create a compelling, varied video concept
        # Use diverse hooks and value propositions to avoid repetition
        
        # Diverse hook options
        hooks = [
            f"Discover how {main_topic} is revolutionizing the AI industry.",
            f"Explore the cutting-edge developments in {main_topic}.",
            f"Uncover the latest innovations in {main_topic}.",
            f"Take a deep dive into {main_topic} and its impact on AI.",
            f"Learn about the breakthrough developments in {main_topic}.",
            f"Get insights into how {main_topic} is shaping the future of AI.",
            f"Understand the significance of {main_topic} in today's AI landscape.",
            f"Discover what makes {main_topic} a game-changer for AI.",
        ]
        
        # Diverse content hooks
        content_hooks = [
            "This breakthrough technology is changing everything we know about AI.",
            "Get an exclusive look at what's coming next in AI technology.",
            "Learn what this means for the future of artificial intelligence.",
            "We'll break down the key innovations and their real-world impact.",
            "This technology represents a major shift in how we approach AI.",
            "Join us as we explore the implications and opportunities ahead.",
            "We'll examine the technical breakthroughs and practical applications.",
            "Discover the trends and developments that matter most.",
        ]
        
        # Diverse value propositions
        value_props = [
            "This comprehensive guide breaks down everything you need to know.",
            "We'll explain the key concepts and real-world implications.",
            "We'll dive deep into the technical details and practical applications.",
            "You'll learn the essential insights and what they mean for you.",
            "We'll cover the critical points and why they matter.",
            "This analysis provides actionable insights and expert perspectives.",
            "We'll explore the nuances and help you understand the bigger picture.",
            "Get expert analysis and practical takeaways you can use.",
        ]
        
        # Select hooks based on content analysis for variety
        # Use article characteristics to guide selection
        title_lower = title.lower()
        summary_lower = summary.lower()
        
        # Choose hook based on content
        if any(tag in ['ai startup', 'generative ai', 'llm'] for tag in visual_tags):
            hook = hooks[0]  # "Discover how..."
        elif "new" in title_lower or "breakthrough" in summary_lower:
            hook = hooks[4]  # "Learn about the breakthrough..."
        elif any(word in title_lower for word in ['future', 'next', 'coming']):
            hook = hooks[5]  # "Get insights into how..."
        else:
            # Use hash of title to consistently select different hooks for variety
            hook_index = hash(title) % len(hooks)
            hook = hooks[hook_index]
        
        # Choose content hook
        if "breakthrough" in summary_lower or "revolution" in summary_lower:
            content_hook = content_hooks[0]
        elif any(word in title_lower for word in ['future', 'next', 'coming']):
            content_hook = content_hooks[1]
        else:
            content_hook_index = (hash(title) + 1) % len(content_hooks)
            content_hook = content_hooks[content_hook_index]
        
        # Choose value prop
        if "tutorial" in title_lower or "how" in title_lower:
            value_prop = value_props[0]
        elif "explained" in title_lower or "understanding" in title_lower:
            value_prop = value_props[1]
        else:
            value_prop_index = (hash(title) + 2) % len(value_props)
            value_prop = value_props[value_prop_index]
        
        video_description = f"{hook} {content_hook} {value_prop}"
        
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
        
        # Calculate nuanced scores based on comprehensive content analysis
        title_lower = title.lower()
        summary_lower = summary.lower()
        
        # Trend score: Based on tags, recency indicators, and topic relevance
        trend_score = 0.5  # Base score
        
        # Boost for trending tags
        if any(tag in ['ai startup', 'generative ai', 'llm', 'large language model'] for tag in visual_tags):
            trend_score += 0.15
        elif any(tag in ['neural network', 'deep learning', 'computer vision'] for tag in visual_tags):
            trend_score += 0.10
        
        # Boost for recency indicators
        if any(word in title_lower for word in ['new', 'latest', 'recent', 'announces', 'unveils']):
            trend_score += 0.10
        elif any(word in summary_lower[:200] for word in ['announced', 'released', 'launched', 'unveiled']):
            trend_score += 0.08
        
        # Boost for breakthrough/innovation language
        if any(word in summary_lower for word in ['breakthrough', 'revolutionary', 'game-changer', 'milestone']):
            trend_score += 0.12
        
        # Cap at 1.0
        trend_score = min(trend_score, 1.0)
        
        # SEO score: Based on keyword count, topic specificity, and searchability
        seo_score = 0.4  # Base score
        
        # Boost for keyword count
        keyword_count = len(target_keywords)
        if keyword_count >= 7:
            seo_score += 0.25
        elif keyword_count >= 5:
            seo_score += 0.20
        elif keyword_count >= 3:
            seo_score += 0.15
        
        # Boost for specific AI/ML terms (better search intent)
        specific_terms = ['llm', 'gpt', 'claude', 'transformer', 'neural', 'deep learning']
        if any(term in summary_lower for term in specific_terms):
            seo_score += 0.15
        
        # Boost for question/explainer format (better search intent)
        if any(word in title_lower for word in ['how', 'what', 'why', 'explained', 'guide']):
            seo_score += 0.10
        
        # Cap at 1.0
        seo_score = min(seo_score, 1.0)
        
        # Uniqueness score: Based on novelty, specificity, and differentiation
        uniqueness_score = 0.4  # Base score
        
        # Boost for novelty indicators
        if any(word in title_lower for word in ['new', 'first', 'breakthrough', 'unveils', 'announces']):
            uniqueness_score += 0.20
        elif "breakthrough" in summary_lower or "revolutionary" in summary_lower:
            uniqueness_score += 0.15
        
        # Boost for specific company/product mentions (more unique than generic topics)
        if any(word in title_lower for word in ['openai', 'google', 'microsoft', 'anthropic', 'meta']):
            uniqueness_score += 0.15
        
        # Boost for specific technology mentions
        if any(word in summary_lower for word in ['gpt-', 'claude', 'gemini', 'llama', 'mistral']):
            uniqueness_score += 0.10
        
        # Penalty for very generic topics
        if main_topic.lower() in ['ai', 'artificial intelligence', 'technology', 'machine learning']:
            uniqueness_score -= 0.10
        
        # Cap between 0.0 and 1.0
        uniqueness_score = max(0.0, min(uniqueness_score, 1.0))
        
        # Engagement score: Weighted average
        engagement_score = (trend_score * 0.4 + seo_score * 0.35 + uniqueness_score * 0.25)
        
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
            
            # Generate 1 video idea per article (faster processing)
            # Note: All articles here have already been accepted into the feed, so generate ideas for all
            num_ideas = 1  # Generate 1 idea per article for faster processing
            
            # Generate video idea with improved prompt structure
            video_ideas_data = generate_video_ideas_for_article(item, num_ideas=num_ideas)
            
            if not video_ideas_data:
                logger.error(f"Video idea generation failed for article {i}: {title[:50]}... - No video ideas generated")
                continue
            
            # Format each video idea
            for idea_num, video_idea_data in enumerate(video_ideas_data):
                video_idea = {
                    'title': video_idea_data.get('video_title', title),
                    'description': video_idea_data.get('video_description', summary),
                    'concept_summary': video_idea_data.get('concept_summary', ''),
                    'why_matters_builders': video_idea_data.get('why_matters_builders', ''),
                    'example_workflow': video_idea_data.get('example_workflow', ''),
                    'predicted_impact': video_idea_data.get('predicted_impact', ''),
                    'source': source,
                    'source_url': source_url,
                    'generated_date': datetime.utcnow().isoformat(),
                    'type': 'video_idea',
                    # Video idea analysis fields
                    'trend_analysis': video_idea_data.get('trend_analysis', ''),
                    'virality_factors': video_idea_data.get('virality_factors', []),
                    'target_keywords': video_idea_data.get('target_keywords', []),
                    'content_outline': video_idea_data.get('content_outline', []),
                    'target_duration_minutes': video_idea_data.get('target_duration_minutes', 10),
                    'estimated_engagement_score': video_idea_data.get('estimated_engagement_score', 0.5),
                    'trend_score': video_idea_data.get('trend_score', 0.5),
                    'seo_score': video_idea_data.get('seo_score', 0.5),
                    'uniqueness_score': video_idea_data.get('uniqueness_score', 0.5),
                    'automation_angle': video_idea_data.get('automation_angle', ''),
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

