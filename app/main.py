"""
Flask application for AI News Tracker API.

Provides REST API endpoints for news feed access, pipeline triggers, and webhooks.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json

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


@app.route('/api/refresh', methods=['POST'])
def refresh_feed():
    """
    Update feed.json with new data.
    
    Expected JSON body:
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
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        if 'items' not in data:
            return jsonify({'error': 'Missing required field: items'}), 400
        
        # Save to feed.json
        save_json(data, settings.FEED_FILE)
        
        item_count = len(data.get('items', []))
        logger.info(f"Feed refreshed with {item_count} items")
        
        return jsonify({
            'status': 'success',
            'message': f'Feed updated with {item_count} items'
        }), 200
        
    except Exception as e:
        logger.error(f"Error refreshing feed: {e}")
        return jsonify({'error': 'Failed to refresh feed'}), 500


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

