"""
Flask application for AI News Tracker API.

Provides REST API endpoints for news feed access, pipeline triggers, and webhooks.
"""

import subprocess
import os
import glob
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json, merge_feeds, generate_feed_json

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for web frontend
CORS(app)

# Initialize logger
logger = setup_logger(__name__)


def cleanup_old_data():
    """
    Clean up old feed data and thumbnail images before starting a new pipeline run.
    """
    logger.info("Cleaning up old feed data and images")
    
    data_dir = settings.DATA_DIR
    removed_count = 0
    
    # Remove JSON data files
    data_files = [
        settings.RAW_NEWS_FILE,
        settings.SUMMARIES_FILE,
        settings.VIDEO_IDEAS_FILE,
        settings.THUMBNAILS_FILE,
        settings.FEED_FILE,
    ]
    
    for filename in data_files:
        file_path = settings.get_data_file_path(filename)
        if file_path.exists():
            try:
                file_path.unlink()
                removed_count += 1
                logger.info(f"Removed: {filename}")
            except Exception as e:
                logger.warning(f"Failed to remove {filename}: {e}")
    
    # Remove thumbnail image files (thumbnail_*.png)
    try:
        image_pattern = str(data_dir / "thumbnail_*.png")
        image_files = glob.glob(image_pattern)
        for image_file in image_files:
            try:
                os.remove(image_file)
                removed_count += 1
                logger.info(f"Removed image: {Path(image_file).name}")
            except Exception as e:
                logger.warning(f"Failed to remove image {image_file}: {e}")
        
        if image_files:
            logger.info(f"Removed {len(image_files)} thumbnail image(s)")
    except Exception as e:
        logger.warning(f"Error removing thumbnail images: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleanup complete: removed {removed_count} file(s)")
    else:
        logger.info("No old data to clean up")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON response with status and service information
    """
    return jsonify({
        'status': 'healthy',
        'service': 'ai-news-tracker',
        'version': '1.0.0'
    }), 200


@app.route('/api/tag-images/<filename>', methods=['GET'])
def serve_tag_image(filename):
    """
    Serve tag images from the tag_images directory.
    
    Args:
        filename: Name of the tag image file (e.g., tag_001.png)
    
    Returns:
        Image file or 404 if not found
    """
    try:
        tag_images_dir = settings.DATA_DIR / "tag_images"
        tag_images_path = tag_images_dir / filename
        
        # Log for debugging
        logger.info(f"Serving tag image: {tag_images_path} (exists: {tag_images_path.exists()})")
        logger.info(f"DATA_DIR: {settings.DATA_DIR}, tag_images_dir: {tag_images_dir}")
        
        if not tag_images_dir.exists():
            logger.error(f"Tag images directory does not exist: {tag_images_dir}")
            return jsonify({'error': f'Tag images directory not found'}), 404
        
        if not tag_images_path.exists():
            logger.warning(f"Tag image not found: {tag_images_path}")
            # List available files for debugging
            available = list(tag_images_dir.glob("*.png"))
            logger.warning(f"Available tag images: {[f.name for f in available[:5]]}")
            return jsonify({'error': f'Tag image not found: {filename}'}), 404
        
        return send_from_directory(str(tag_images_dir), filename)
    except Exception as e:
        logger.error(f"Error serving tag image {filename}: {e}", exc_info=True)
        return jsonify({'error': f'Tag image error: {str(e)}'}), 404


@app.route('/api/news', methods=['GET'])
def get_news_feed():
    """
    Get current news feed.
    
    Returns:
        JSON response with feed data or empty array if feed.json doesn't exist
    """
    try:
        feed_data = load_json(settings.FEED_FILE)
        items = feed_data.get('items', [])
        logger.info(f"Returning {len(items)} feed items")
        return jsonify(items), 200
    except FileNotFoundError:
        logger.warning(f"Feed file not found: {settings.FEED_FILE}")
        return jsonify([]), 200
    except Exception as e:
        logger.error(f"Error loading feed: {e}")
        return jsonify({'error': 'Failed to load feed'}), 500


@app.route('/api/refresh', methods=['GET', 'POST'])
def refresh_feed():
    """
    Update feed.json with new data.
    
    For GET requests or POST without body: Merges data from summaries.json, 
    video_ideas.json, and thumbnails.json into feed.json.
    
    For POST with JSON body:
        {
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00",
            "items": [...],
            "total_items": 10
        }
    
    Returns:
        JSON response with success status
    """
    try:
        # Default feed limit
        feed_limit = 30
        
        # For GET requests, always merge from data files
        if request.method == 'GET':
            logger.info("Merging feed from data files (GET request)")
            try:
                # Load all pipeline outputs
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                thumbnails = load_json(settings.THUMBNAILS_FILE).get('items', [])
                
                # Merge and generate feed with filtering and limit
                merged_data = merge_feeds(news_items, video_ideas, thumbnails, apply_filtering=True, max_items=feed_limit)
                generate_feed_json(merged_data)
                
                item_count = len(merged_data)
                logger.info(f"Feed refreshed with {item_count} items from data files")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Feed updated with {item_count} items',
                    'items_count': item_count
                }), 200
            except FileNotFoundError as e:
                logger.warning(f"Data file not found: {e}")
                return jsonify({
                    'status': 'warning',
                    'message': 'Some data files not found, feed may be incomplete'
                }), 200
            except Exception as e:
                logger.error(f"Error merging feed from data files: {e}")
                return jsonify({'error': f'Failed to merge feed: {str(e)}'}), 500
        
        # POST request: try to get JSON body, but fall back to merging from files if no body
        data = None
        if request.is_json:
            data = request.get_json(silent=True)
        
        # If no body provided or not JSON, merge from data files
        if not data:
            logger.info("Merging feed from data files (POST without body)")
            try:
                # Load all pipeline outputs
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                thumbnails = load_json(settings.THUMBNAILS_FILE).get('items', [])
                
                # Merge and generate feed (use default limit of 12)
                merged_data = merge_feeds(news_items, video_ideas, thumbnails, max_items=12)
                generate_feed_json(merged_data)
                
                item_count = len(merged_data)
                logger.info(f"Feed refreshed with {item_count} items from data files")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Feed updated with {item_count} items',
                    'items_count': item_count
                }), 200
            except FileNotFoundError as e:
                logger.warning(f"Data file not found: {e}")
                return jsonify({
                    'status': 'warning',
                    'message': 'Some data files not found, feed may be incomplete'
                }), 200
            except Exception as e:
                logger.error(f"Error merging feed from data files: {e}")
                return jsonify({'error': f'Failed to merge feed: {str(e)}'}), 500
        
        # POST with body: validate and save directly
        if 'items' not in data:
            return jsonify({'error': 'Missing required field: items'}), 400
        
        # Save to feed.json
        save_json(data, settings.FEED_FILE)
        
        item_count = len(data.get('items', []))
        logger.info(f"Feed refreshed with {item_count} items from POST body")
        
        return jsonify({
            'status': 'success',
            'message': f'Feed updated with {item_count} items',
            'items_count': item_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error refreshing feed: {e}")
        return jsonify({'error': 'Failed to refresh feed'}), 500


@app.route('/api/scrape', methods=['GET'])
def scrape_feeds():
    """
    Trigger RSS feed scraping.
    
    Returns:
        JSON response with scraping status
    """
    try:
        # Clean up old data before starting new pipeline
        cleanup_old_data()
        
        logger.info("Triggering RSS feed scraping")
        result = subprocess.run(
            ['python', '/app/app/scripts/rss_scraper.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("RSS scraping completed successfully")
            return jsonify({
                'status': 'success',
                'message': 'RSS feeds scraped successfully'
            }), 200
        else:
            logger.error(f"RSS scraping failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'RSS scraping failed',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("RSS scraping timed out")
        return jsonify({'error': 'Scraping timed out'}), 500
    except Exception as e:
        logger.error(f"Error triggering RSS scraping: {e}")
        return jsonify({'error': 'Failed to trigger scraping'}), 500


@app.route('/api/summarize', methods=['GET', 'POST'])
def summarize_articles():
    """
    Trigger article summarization.
    
    Returns:
        JSON response with summarization status
    """
    try:
        logger.info("Triggering article summarization")
        result = subprocess.run(
            ['python', '/app/app/scripts/summarizer.py'],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            logger.info("Summarization completed successfully")
            return jsonify({
                'status': 'success',
                'message': 'Articles summarized successfully'
            }), 200
        else:
            logger.error(f"Summarization failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Summarization failed',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("Summarization timed out")
        return jsonify({'error': 'Summarization timed out'}), 500
    except Exception as e:
        logger.error(f"Error triggering summarization: {e}")
        return jsonify({'error': 'Failed to trigger summarization'}), 500


@app.route('/api/generate-ideas', methods=['GET', 'POST'])
def generate_ideas():
    """
    Trigger video idea generation.
    
    Returns:
        JSON response with generation status
    """
    try:
        logger.info("Triggering video idea generation")
        result = subprocess.run(
            ['python', '/app/app/scripts/video_idea_generator.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("Video idea generation completed successfully")
            return jsonify({
                'status': 'success',
                'message': 'Video ideas generated successfully'
            }), 200
        else:
            logger.error(f"Video idea generation failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Video idea generation failed',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("Video idea generation timed out")
        return jsonify({'error': 'Generation timed out'}), 500
    except Exception as e:
        logger.error(f"Error triggering video idea generation: {e}")
        return jsonify({'error': 'Failed to trigger generation'}), 500


# DEPRECATED: Thumbnail generation removed from pipeline
# Tag images are now pre-generated separately using generate_tag_images.sh
@app.route('/api/generate-thumbnails', methods=['GET', 'POST'])
def generate_thumbnails():
    """
    DEPRECATED: Thumbnail generation removed from pipeline.
    Tag images are now pre-generated separately using generate_tag_images.sh.
    
    Returns:
        JSON response with instructions
    """
    return jsonify({
        'status': 'info',
        'message': 'Thumbnail generation removed from pipeline. Use generate_tag_images.sh to generate tag images separately.',
        'instructions': 'Run: bash app/scripts/generate_tag_images.sh'
    }), 200


@app.route('/webhook/n8n', methods=['POST'])
def n8n_webhook():
    """
    Receive webhook callbacks from n8n workflows.
    
    Expected JSON body:
        {
            "workflow": "ai-news-pipeline",
            "status": "completed",
            "data": {...}
        }
    
    Returns:
        JSON response acknowledging receipt
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        workflow = data.get('workflow', 'unknown')
        status = data.get('status', 'unknown')
        
        logger.info(f"Received n8n webhook: workflow={workflow}, status={status}")
        
        # If workflow completed successfully, merge data and update feed
        if status == 'completed' and 'data' in data:
            try:
                # Load all pipeline outputs
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                thumbnails = load_json(settings.THUMBNAILS_FILE).get('items', [])
                
                # Merge and generate feed with limit (default 12)
                feed_limit = getattr(settings, 'FEED_LIMIT', 30)
                merged_data = merge_feeds(news_items, video_ideas, thumbnails, apply_filtering=True, max_items=feed_limit)
                generate_feed_json(merged_data)
                
                logger.info(f"Feed updated from n8n webhook: {len(merged_data)} items")
            except Exception as e:
                logger.error(f"Error processing webhook data: {e}")
        
        return jsonify({
            'status': 'received',
            'message': 'Webhook processed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing n8n webhook: {e}")
        return jsonify({'error': 'Failed to process webhook'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    """Run Flask development server."""
    app.run(
        host='0.0.0.0',
        port=settings.PYTHON_APP_PORT,
        debug=True
    )

