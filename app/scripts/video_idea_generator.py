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

logger = setup_logger(__name__)

# Try to import Google Generative AI, fallback to template-based if not available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    if settings.GOOGLE_AI_API_KEY:
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        logger.info("Google AI Studio (Gemini) configured")
    else:
        GEMINI_AVAILABLE = False
        logger.warning("GOOGLE_AI_API_KEY not set, falling back to template-based generation")
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed, falling back to template-based generation")

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


def generate_video_idea_with_gemini(item: Dict[str, Any], idea_index: int = 0) -> Optional[Dict[str, Any]]:
    """
    Generate video idea using Google AI Studio (Gemini) with improved prompt.
    
    Args:
        item: Article dictionary with title, summary, etc.
        idea_index: Index of idea being generated (0-based) for variety
        
    Returns:
        Video idea dictionary or None if generation fails
    """
    if not GEMINI_AVAILABLE or not settings.GOOGLE_AI_API_KEY:
        return None
    
    try:
        title = item.get('title', '')
        summary = item.get('summary', '')
        visual_tags = item.get('visual_tags', [])
        
        # Validate input
        combined_text = f"{title} {summary}"
        is_valid, sanitized_text, reason = validate_for_video_ideas(combined_text)
        if not is_valid:
            logger.warning(f"Input validation failed: {reason}")
            return None
        
        # Extract topics and AI angle for context
        topics = extract_key_topics(sanitized_text, max_topics=5)
        main_topic = topics[0] if topics else "AI Technology"
        automation_angle = extract_automation_angle(title, summary)
        
        # Determine angle focus based on idea index
        text_lower = sanitized_text.lower()
        is_breakthrough = any(word in text_lower for word in ['breakthrough', 'revolutionary', 'game-changer'])
        is_announcement = any(word in text_lower for word in ['announces', 'unveils', 'launches', 'releases'])
        is_exec_change = any(word in text_lower for word in ['executive', 'ceo', 'leaves', 'departs', 'resigns'])
        is_strategy_shift = any(word in text_lower for word in ['strategy', 'pivot', 'shift', 'change', 'new direction'])
        
        if idea_index == 0:
            angle_focus = "immediate implications"
        elif idea_index == 1:
            angle_focus = "hidden implications"
        else:
            angle_focus = automation_angle
        
        # Improved prompt for Gemini
        prompt = f"""You are an expert AI industry analyst and technical content strategist for an AI community (builders, indie hackers, freelancers, and AI engineers).

Your task is to take this curated news item and generate a video idea that is:

1. **Audience-Relevant**: Focus on practical implications for AI builders and indie hackers. Highlight how this tech can be exploited, what workflows it enables, and how it changes AI opportunities.

2. **Action-Heavy**: Tell viewers what they can do next (tools to try, workflows to build, threats/opportunities, market shifts).

3. **Signal > Noise**: Avoid generic summaries. Produce concrete, angle-driven, story-worthy video ideas.

4. **Unique Angle**: Include:
   - A strong hook
   - A clear audience value proposition
   - A builder/angle (why this matters to people who make AI tools and workflows)
   - At least one example application
   - A takeaway or prediction

**Article:**
Title: {title}
Summary: {summary}

**Focus Angle:** {angle_focus}

**Output Format (JSON):**
{{
  "title": "Strong hook title",
  "concept_summary": "2-3 sentences describing the video concept",
  "why_matters_builders": "Why this matters for AI builders",
  "example_workflow": "Example workflow or use case",
  "predicted_impact": "One sentence prediction"
}}

Generate ONE high-value video idea focused on AI builders with a {angle_focus} angle."""
        
        # Generate with Gemini
        model = genai.GenerativeModel(settings.GOOGLE_AI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 500,
            }
        )
        
        # Parse response
        response_text = response.text.strip()
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                idea_data = json.loads(json_match.group())
            except json.JSONDecodeError:
                # Fallback: parse manually
                idea_data = {}
                idea_data['title'] = re.search(r'"title":\s*"([^"]+)"', response_text)
                idea_data['concept_summary'] = re.search(r'"concept_summary":\s*"([^"]+)"', response_text)
                idea_data['why_matters_builders'] = re.search(r'"why_matters_builders":\s*"([^"]+)"', response_text)
                idea_data['example_workflow'] = re.search(r'"example_workflow":\s*"([^"]+)"', response_text)
                idea_data['predicted_impact'] = re.search(r'"predicted_impact":\s*"([^"]+)"', response_text)
                idea_data = {k: v.group(1) if v else "" for k, v in idea_data.items()}
        else:
            # Fallback: use response as description
            idea_data = {
                'title': f"{main_topic}: What Builders Need to Know",
                'concept_summary': response_text[:200],
                'why_matters_builders': "This development impacts AI builders and workflow creators.",
                'example_workflow': "Build workflows leveraging this technology.",
                'predicted_impact': "This will reshape AI opportunities."
            }
        
        # Extract topics for keywords
        target_keywords = topics[:5] if topics else [main_topic]
        target_keywords.extend([automation_angle, "automation", "AI builders", "workflow"])
        target_keywords = list(dict.fromkeys(target_keywords))[:8]
        
        # Build description from components
        video_description = f"{idea_data.get('concept_summary', '')}\n\nWhy This Matters for AI Builders: {idea_data.get('why_matters_builders', '')}\n\nExample Workflow: {idea_data.get('example_workflow', '')}\n\nPredicted Impact: {idea_data.get('predicted_impact', '')}"
        
        # Generate trend analysis
        trend_analysis = f"This topic represents current developments in {main_topic} with significant potential for AI builders. "
        if any(tag in ['ai startup', 'generative ai', 'llm', 'large language model'] for tag in visual_tags):
            trend_analysis += "The technology is trending in the AI  community and has high practical value."
        else:
            trend_analysis += "The topic has growing interest and direct applications for AI workflows."
        
        # Select virality factors
        selected_factors = [
            "Practical value for AI builders",
            "Action-oriented content",
            "Real-world workflow applications",
        ]
        if is_breakthrough:
            selected_factors.append("Novel or breakthrough technology")
        if is_announcement:
            selected_factors.append("Timely and trending topic")
        
        # Calculate scores
        trend_score = 0.6 if is_announcement or is_breakthrough else 0.5
        seo_score = 0.7 if len(target_keywords) >= 6 else 0.5
        uniqueness_score = 0.8 if is_breakthrough or is_exec_change else 0.6
        engagement_score = (trend_score * 0.4 + seo_score * 0.35 + uniqueness_score * 0.25)
        
        video_idea = {
            'video_title': idea_data.get('title', f"{main_topic}: What Builders Need to Know"),
            'video_description': video_description,
            'concept_summary': idea_data.get('concept_summary', ''),
            'why_matters_builders': idea_data.get('why_matters_builders', ''),
            'example_workflow': idea_data.get('example_workflow', ''),
            'predicted_impact': idea_data.get('predicted_impact', ''),
            'trend_analysis': trend_analysis,
            'virality_factors': selected_factors,
            'target_keywords': target_keywords,
            'content_outline': [
                f"Introduction: Hook with {main_topic} and why builders should care",
                f"Main content: Deep dive into {angle_focus} and practical implications",
                f"Example workflow: {idea_data.get('example_workflow', 'Workflow demonstration')}",
                f"Conclusion: {idea_data.get('predicted_impact', 'Actionable next steps')} and actionable next steps",
            ],
            'target_duration_minutes': 10,
            'estimated_engagement_score': round(engagement_score, 2),
            'trend_score': round(trend_score, 2),
            'seo_score': round(seo_score, 2),
            'uniqueness_score': round(uniqueness_score, 2),
            'automation_angle': automation_angle,
        }
        
        logger.debug(f"Generated video idea {idea_index + 1} with Gemini: {video_idea['video_title'][:50]}...")
        return video_idea
        
    except Exception as e:
        logger.error(f"Failed to generate video idea with Gemini: {e}", exc_info=True)
        return None


def generate_video_ideas_for_article(item: Dict[str, Any], num_ideas: int = 3) -> List[Dict[str, Any]]:
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
        
        video_ideas = []
        
        # Use Gemini for all ideas if available
        use_gemini = GEMINI_AVAILABLE and settings.GOOGLE_AI_API_KEY
        
        if not use_gemini:
            logger.warning("Gemini not available, cannot generate video ideas")
            return []
        
        # Generate 3-5 unique video ideas with different angles using Gemini
        for i in range(num_ideas):
            gemini_idea = generate_video_idea_with_gemini(item, idea_index=i)
            if gemini_idea:
                video_ideas.append(gemini_idea)
                # Add small delay to avoid rate limiting (Gemini free tier: 15 req/min)
                if i < num_ideas - 1:
                    import time
                    time.sleep(4)  # ~15 requests per minute max
            else:
                logger.warning(f"Failed to generate idea {i+1}/{num_ideas} with Gemini, skipping")
        
        logger.debug(f"Generated {len(video_ideas)} video ideas for: {title[:50]}...")
        return video_ideas
        
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
            num_ideas = random.randint(3, 5)  # Generate 3-5 ideas per article
            
            # Generate multiple video ideas with improved prompt structure
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
