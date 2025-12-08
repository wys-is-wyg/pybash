"""
Flask application for AI News Tracker API.

Provides REST API endpoints for news feed access, pipeline triggers, and webhooks.
"""

import subprocess
import os
import time
import requests
import smtplib
import threading
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

# Pipeline progress tracking
pipeline_progress = {
    'status': 'idle',  # idle, running, completed, error
    'current_step': '',
    'progress_percent': 0,
    'start_time': None,
    'estimated_seconds_remaining': None,
    'message': ''
}
progress_lock = threading.Lock()


def cleanup_old_data():
    """
    Clean up old feed data files before starting a new pipeline run.
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
                # Load all pipeline outputs (use summaries.json, not raw_news.json)
                news_items = load_json(settings.SUMMARIES_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                
                # Merge and generate feed with filtering and limit (tag images are pre-generated)
                merged_data = merge_feeds(news_items, video_ideas, apply_filtering=True, max_items=feed_limit)
                generate_feed_json(merged_data)
                
                item_count = len(merged_data)
                logger.info(f"Feed refreshed with {item_count} items from data files")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Feed updated with {item_count} items',
                    'items_count': item_count
                }), 200
            except FileNotFoundError as e:
                logger.error(f"Required data file not found: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Required data file not found: {str(e)}'
                }), 500
            except Exception as e:
                logger.error(f"Error merging feed from data files: {e}", exc_info=True)
                return jsonify({'error': f'Failed to merge feed: {str(e)}'}), 500
        
        # POST request: try to get JSON body, but fall back to merging from files if no body
        data = None
        if request.is_json:
            data = request.get_json(silent=True)
        
        # If no body provided or not JSON, merge from data files
        if not data:
            logger.info("Merging feed from data files (POST without body)")
            try:
                # Load all pipeline outputs (use summaries.json, not raw_news.json)
                news_items = load_json(settings.SUMMARIES_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                
                # Merge and generate feed (use default limit of 12, tag images are pre-generated)
                merged_data = merge_feeds(news_items, video_ideas, max_items=12)
                generate_feed_json(merged_data)
                
                item_count = len(merged_data)
                logger.info(f"Feed refreshed with {item_count} items from data files")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Feed updated with {item_count} items',
                    'items_count': item_count
                }), 200
            except FileNotFoundError as e:
                logger.error(f"Required data file not found: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Required data file not found: {str(e)}'
                }), 500
            except Exception as e:
                logger.error(f"Error merging feed from data files: {e}", exc_info=True)
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
                # Load all pipeline outputs (tag images are pre-generated)
                news_items = load_json(settings.RAW_NEWS_FILE).get('items', [])
                video_ideas = load_json(settings.VIDEO_IDEAS_FILE).get('items', [])
                
                # Merge and generate feed with limit (default 12)
                feed_limit = getattr(settings, 'FEED_LIMIT', 30)
                merged_data = merge_feeds(news_items, video_ideas, apply_filtering=True, max_items=feed_limit)
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


def monitor_pipeline_progress():
    """Monitor pipeline progress by checking data files and estimating based on typical stages."""
    global pipeline_progress
    
    # Pipeline step estimates (in seconds) - updated for faster processing with 1 idea per article
    STEP_ESTIMATES = {
        'scraping': 10,
        'summarization': 30,
        'video_ideas': 10,  # Faster with 1 idea per article
        'merging': 5,
    }
    TOTAL_ESTIMATE = sum(STEP_ESTIMATES.values())
    
    feed_file = settings.get_data_file_path(settings.FEED_FILE)
    raw_news_file = settings.get_data_file_path(settings.RAW_NEWS_FILE)
    summaries_file = settings.get_data_file_path(settings.SUMMARIES_FILE)
    video_ideas_file = settings.get_data_file_path(settings.VIDEO_IDEAS_FILE)
    
    start_time = pipeline_progress['start_time']
    max_wait_time = 120  # 2 minutes max
    
    while time.time() - start_time < max_wait_time:
        elapsed = time.time() - start_time
        
        # Determine current step based on file existence
        if raw_news_file.exists():
            if summaries_file.exists():
                if video_ideas_file.exists():
                    if feed_file.exists():
                        # Pipeline completed
                        with progress_lock:
                            pipeline_progress['status'] = 'completed'
                            pipeline_progress['current_step'] = 'Pipeline completed'
                            pipeline_progress['progress_percent'] = 100
                            pipeline_progress['estimated_seconds_remaining'] = 0
                            pipeline_progress['message'] = 'Pipeline completed successfully'
                        logger.info("Pipeline completed successfully")
                        return
                    else:
                        # Merging stage
                        step_progress = min(elapsed / TOTAL_ESTIMATE, 0.95)
                        remaining = TOTAL_ESTIMATE * (1 - step_progress)
                        with progress_lock:
                            pipeline_progress['current_step'] = 'Merging feed data...'
                            pipeline_progress['progress_percent'] = int(90 + (step_progress * 10))
                            pipeline_progress['estimated_seconds_remaining'] = max(0, int(remaining))
                else:
                    # Video ideas stage
                    step_progress = min((elapsed - 40) / STEP_ESTIMATES['video_ideas'], 1.0)
                    remaining = STEP_ESTIMATES['video_ideas'] * (1 - step_progress) + STEP_ESTIMATES['merging']
                    with progress_lock:
                        pipeline_progress['current_step'] = 'Generating video ideas...'
                        pipeline_progress['progress_percent'] = int(60 + (step_progress * 30))
                        pipeline_progress['estimated_seconds_remaining'] = max(0, int(remaining))
            else:
                # Summarization stage
                step_progress = min((elapsed - 10) / STEP_ESTIMATES['summarization'], 1.0)
                remaining = STEP_ESTIMATES['summarization'] * (1 - step_progress) + STEP_ESTIMATES['video_ideas'] + STEP_ESTIMATES['merging']
                with progress_lock:
                    pipeline_progress['current_step'] = 'Summarizing articles...'
                    pipeline_progress['progress_percent'] = int(20 + (step_progress * 40))
                    pipeline_progress['estimated_seconds_remaining'] = max(0, int(remaining))
        else:
            # Scraping stage
            step_progress = min(elapsed / STEP_ESTIMATES['scraping'], 1.0)
            remaining = TOTAL_ESTIMATE * (1 - step_progress)
            with progress_lock:
                pipeline_progress['current_step'] = 'Scraping RSS feeds...'
                pipeline_progress['progress_percent'] = int(step_progress * 20)
                pipeline_progress['estimated_seconds_remaining'] = max(0, int(remaining))
        
        time.sleep(2)  # Check every 2 seconds
    
    # Timeout
    with progress_lock:
        if pipeline_progress['status'] == 'running':
            pipeline_progress['status'] = 'timeout'
            pipeline_progress['current_step'] = 'Pipeline taking longer than expected'
            pipeline_progress['message'] = 'Pipeline may still be running'
    logger.warning("Pipeline progress monitoring timed out")


@app.route('/api/pipeline-progress', methods=['GET'])
def get_pipeline_progress():
    """Get current pipeline progress."""
    with progress_lock:
        progress = pipeline_progress.copy()
    
    # Calculate elapsed time if running
    if progress['status'] == 'running' and progress['start_time']:
        elapsed = time.time() - progress['start_time']
        progress['elapsed_seconds'] = int(elapsed)
    else:
        progress['elapsed_seconds'] = 0
    
    return jsonify(progress), 200


@app.route('/api/trigger-pipeline', methods=['POST'])
def trigger_pipeline():
    """
    Trigger the n8n webhook pipeline with progress tracking.
    
    Returns:
        JSON response with status and message
    """
    global pipeline_progress
    
    try:
        # Check if pipeline is already running
        with progress_lock:
            if pipeline_progress['status'] == 'running':
                return jsonify({
                    'status': 'error',
                    'message': 'Pipeline is already running'
                }), 400
        
        # Get webhook URL from environment
        webhook_url = os.getenv('N8N_WEBHOOK_URL', '')
        
        # If not set, or if it contains localhost (wrong for Docker), use Docker service name
        if not webhook_url or 'localhost' in webhook_url or '127.0.0.1' in webhook_url:
            # Use Docker service name for container-to-container communication
            n8n_port = settings.N8N_PORT
            webhook_url = f"http://n8n:{n8n_port}/webhook/run-pipeline"
            logger.info(f"Using Docker service webhook URL: {webhook_url}")
        else:
            logger.info(f"Using configured webhook URL from environment")
        
        # Initialize progress tracking
        with progress_lock:
            pipeline_progress['status'] = 'running'
            pipeline_progress['start_time'] = time.time()
            pipeline_progress['current_step'] = 'Starting pipeline...'
            pipeline_progress['progress_percent'] = 0
            pipeline_progress['estimated_seconds_remaining'] = 55  # Total estimate
            pipeline_progress['message'] = 'Pipeline started'
        
        # Construct payload
        import datetime
        payload = {
            "trigger_source": "web_ui",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "triggered_by": "web_ui_button"
        }
        
        logger.info(f"Triggering n8n webhook: {webhook_url}")
        
        # Send webhook request
        webhook_triggered = False
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10  # Short timeout - we just need to send the request
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook acknowledged with status {response.status_code}")
                webhook_triggered = True
            else:
                logger.warning(f"Webhook returned unexpected status {response.status_code}: {response.text}")
                webhook_triggered = True
                
        except requests.exceptions.Timeout:
            # Timeout is OK - n8n may have accepted the request but not responded yet
            logger.info("Webhook request timed out (workflow may still be running)")
            webhook_triggered = True
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to n8n webhook: {e}")
            with progress_lock:
                pipeline_progress['status'] = 'error'
                pipeline_progress['message'] = f'Failed to connect to n8n: {str(e)}'
            return jsonify({
                'status': 'error',
                'message': f'Failed to connect to n8n: {str(e)}'
            }), 500
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending webhook request: {e}")
            with progress_lock:
                pipeline_progress['status'] = 'error'
                pipeline_progress['message'] = f'Failed to trigger webhook: {str(e)}'
            return jsonify({
                'status': 'error',
                'message': f'Failed to trigger webhook: {str(e)}'
            }), 500
        
        if not webhook_triggered:
            with progress_lock:
                pipeline_progress['status'] = 'error'
                pipeline_progress['message'] = 'Failed to trigger webhook'
            return jsonify({
                'status': 'error',
                'message': 'Failed to trigger webhook'
            }), 500
        
        # Start progress monitoring in background thread
        thread = threading.Thread(target=monitor_pipeline_progress, daemon=True)
        thread.start()
        
        # Return immediately with status
        return jsonify({
            'status': 'success',
            'message': 'Pipeline started',
            'poll_endpoint': '/api/pipeline-progress'
        }), 200
        
    except Exception as e:
        logger.error(f"Error triggering pipeline: {e}", exc_info=True)
        with progress_lock:
            pipeline_progress['status'] = 'error'
            pipeline_progress['message'] = f'Failed to trigger pipeline: {str(e)}'
        return jsonify({
            'status': 'error',
            'message': f'Failed to trigger pipeline: {str(e)}'
        }), 500


@app.route('/api/contact', methods=['POST'])
def contact_form():
    """
    Handle contact form submissions and send email.
    
    Expected JSON body:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Question about AI News",
            "message": "Hello, I have a question..."
        }
    
    Returns:
        JSON response with status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'Missing or empty field: {field}'}), 400
        
        name = data['name'].strip()
        email = data['email'].strip()
        subject = data['subject'].strip()
        message = data['message'].strip()
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({'error': 'Invalid email address'}), 400
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = settings.CONTACT_EMAIL
        msg['Subject'] = f"Contact Form: {subject}"
        
        # Email body
        body = f"""
New contact form submission from AI News Tracker:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

---
This message was sent from the AI News Tracker contact form.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email via SMTP
        try:
            smtp_server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            
            if settings.SMTP_USE_TLS:
                smtp_server.starttls()
            
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp_server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            smtp_server.send_message(msg)
            smtp_server.quit()
            
            logger.info(f"Contact form submitted: {name} ({email}) - {subject}")
            
            return jsonify({
                'status': 'success',
                'message': 'Your message has been sent successfully!'
            }), 200
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return jsonify({
                'error': 'Failed to send email. Please try again later.'
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing contact form: {e}")
        return jsonify({'error': 'Failed to process contact form'}), 500


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

