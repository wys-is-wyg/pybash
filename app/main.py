"""
Flask application for AI News Tracker API.

Provides REST API endpoints for news feed access, pipeline triggers, and webhooks.
"""

import subprocess
from flask import Flask, jsonify, request
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
        # For GET requests, always merge from data files
        if request.method == 'GET':
            logger.info("Merging feed from data files (GET request)")
            try:
                # Load all pipeline outputs
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                thumbnails = load_json(settings.THUMBNAILS_FILE).get('items', [])
                
                # Merge and generate feed
                merged_data = merge_feeds(news_items, video_ideas, thumbnails)
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
                
                # Merge and generate feed
                merged_data = merge_feeds(news_items, video_ideas, thumbnails)
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


@app.route('/api/generate-thumbnails', methods=['GET', 'POST'])
def generate_thumbnails():
    """
    Trigger thumbnail generation via Leonardo API.
    
    Returns:
        JSON response with generation status
    """
    try:
        logger.info("Triggering thumbnail generation")
        result = subprocess.run(
            ['python', '/app/app/scripts/leonardo_api.py'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes for batch thumbnail generation
        )
        
        if result.returncode == 0:
            logger.info("Thumbnail generation completed successfully")
            return jsonify({
                'status': 'success',
                'message': 'Thumbnails generated successfully'
            }), 200
        else:
            logger.error(f"Thumbnail generation failed: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': 'Thumbnail generation failed',
                'error': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error("Thumbnail generation timed out")
        return jsonify({'error': 'Generation timed out'}), 500
    except Exception as e:
        logger.error(f"Error triggering thumbnail generation: {e}")
        return jsonify({'error': 'Failed to trigger generation'}), 500


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
                
                # Merge and generate feed
                merged_data = merge_feeds(news_items, video_ideas, thumbnails)
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

