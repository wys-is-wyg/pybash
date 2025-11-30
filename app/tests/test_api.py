"""
API endpoint tests for AI News Tracker.
"""

import json
from pathlib import Path
from app.config import settings


def test_health_endpoint(client):
    """Test GET /health returns 200 with status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'ai-news-tracker'
    assert 'version' in data


def test_get_news_feed_with_file(client, sample_feed_file, mock_feed_data):
    """Test GET /api/news returns feed.json data."""
    response = client.get('/api/news')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['title'] == 'Test News Article'
    assert data[1]['title'] == 'Test Video Idea'


def test_get_news_feed_missing_file(client, temp_data_dir):
    """Test GET /api/news returns empty array if feed.json doesn't exist."""
    # Ensure feed.json doesn't exist
    feed_file = Path(temp_data_dir) / settings.FEED_FILE
    if feed_file.exists():
        feed_file.unlink()
    
    response = client.get('/api/news')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0


def test_refresh_feed_success(client, temp_data_dir):
    """Test POST /api/refresh accepts JSON and updates feed.json."""
    feed_file = Path(temp_data_dir) / settings.FEED_FILE
    
    test_data = {
        'version': '1.0',
        'generated_at': '2024-01-01T00:00:00',
        'items': [
            {
                'type': 'news',
                'title': 'New Article',
                'summary': 'New summary',
                'source': 'New Source',
            }
        ],
        'total_items': 1
    }
    
    response = client.post(
        '/api/refresh',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'message' in data
    
    # Verify file was created/updated
    assert feed_file.exists()
    with open(feed_file) as f:
        saved_data = json.load(f)
    assert saved_data['total_items'] == 1
    assert len(saved_data['items']) == 1


def test_refresh_feed_missing_items(client):
    """Test POST /api/refresh returns 400 if items field is missing."""
    test_data = {
        'version': '1.0',
        'generated_at': '2024-01-01T00:00:00',
    }
    
    response = client.post(
        '/api/refresh',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'items' in data['error'].lower()


def test_refresh_feed_no_json(client):
    """Test POST /api/refresh returns 400 if no JSON provided."""
    response = client.post('/api/refresh')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

