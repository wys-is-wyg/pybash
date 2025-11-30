"""
Pytest configuration and fixtures for API tests.
"""

import json
import tempfile
import shutil
from pathlib import Path
import pytest
from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Temporary data directory fixture."""
    temp_dir = tempfile.mkdtemp()
    
    # Patch settings to use temp directory
    original_data_dir = settings.DATA_DIR
    monkeypatch.setattr(settings, 'DATA_DIR', Path(temp_dir))
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)
    monkeypatch.setattr(settings, 'DATA_DIR', original_data_dir)


@pytest.fixture
def mock_feed_data():
    """Mock feed.json data fixture."""
    return {
        'version': '1.0',
        'generated_at': '2024-01-01T00:00:00',
        'total_items': 2,
        'items': [
            {
                'type': 'news',
                'title': 'Test News Article',
                'summary': 'This is a test news article summary',
                'source': 'Test Source',
                'source_url': 'https://example.com/article1',
                'published_date': '2024-01-01T00:00:00',
            },
            {
                'type': 'video_idea',
                'title': 'Test Video Idea',
                'description': 'This is a test video idea description',
                'source': 'Test Source',
                'source_url': 'https://example.com/article1',
                'thumbnail_url': 'https://example.com/thumb.jpg',
            }
        ]
    }


@pytest.fixture
def sample_feed_file(temp_data_dir, mock_feed_data):
    """Create a sample feed.json file in temp directory."""
    feed_file = Path(temp_data_dir) / settings.FEED_FILE
    with open(feed_file, 'w') as f:
        json.dump(mock_feed_data, f)
    return feed_file

