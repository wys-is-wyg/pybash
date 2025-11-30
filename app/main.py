"""
Flask application for AI News Tracker API.

Provides REST API endpoints for news feed access, pipeline triggers, and webhooks.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from app.config import settings
from app.scripts.logger import setup_logger

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

