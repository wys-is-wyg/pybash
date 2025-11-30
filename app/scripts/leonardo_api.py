"""
Leonardo AI API client for thumbnail generation.

Handles image generation, status polling, and batch processing for video thumbnails.
"""

import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import settings
from app.scripts.logger import setup_logger
from app.scripts.data_manager import load_json, save_json

logger = setup_logger(__name__)

# Global API client state
_api_key = None
_api_headers = None


def initialize_leonardo_client(api_key: str = None) -> None:
    """
    Initialize Leonardo API client with API key.
    
    Args:
        api_key: Leonardo API key (defaults to settings.LEONARDO_API_KEY)
    """
    global _api_key, _api_headers
    
    if api_key is None:
        api_key = settings.LEONARDO_API_KEY
    
    if not api_key:
        raise ValueError("Leonardo API key is required")
    
    _api_key = api_key
    _api_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    logger.info("Leonardo API client initialized")


def generate_thumbnail(prompt: str, model_id: str = None) -> Dict[str, Any]:
    """
    Generate thumbnail image via Leonardo API.
    
    Args:
        prompt: Text prompt for image generation
        model_id: Model ID to use (defaults to settings.LEONARDO_DEFAULT_MODEL_ID)
        
    Returns:
        Dictionary with generation_id and status
    """
    if _api_headers is None:
        initialize_leonardo_client()
    
    if model_id is None:
        model_id = settings.LEONARDO_DEFAULT_MODEL_ID
    
    url = f"{settings.LEONARDO_API_BASE_URL}/generations"
    
    payload = {
        "prompt": prompt,
        "modelId": model_id,
        "width": settings.LEONARDO_THUMBNAIL_WIDTH,
        "height": settings.LEONARDO_THUMBNAIL_HEIGHT,
        "num_images": 1,
    }
    
    logger.debug(f"Generating thumbnail with prompt: {prompt[:50]}...")
    
    try:
        response = requests.post(
            url,
            headers=_api_headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        generation_id = data.get("sdGenerationJob", {}).get("generationId")
        
        if not generation_id:
            raise ValueError("No generation ID returned from API")
        
        logger.info(f"Thumbnail generation started: {generation_id}")
        
        return {
            "generation_id": generation_id,
            "status": "pending",
            "prompt": prompt,
            "model_id": model_id,
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to generate thumbnail: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating thumbnail: {e}")
        raise


def get_generation_status(generation_id: str) -> Dict[str, Any]:
    """
    Poll generation status until complete.
    
    Args:
        generation_id: Generation ID to check
        
    Returns:
        Dictionary with status and image URL if complete
    """
    if _api_headers is None:
        initialize_leonardo_client()
    
    url = f"{settings.LEONARDO_API_BASE_URL}/generations/{generation_id}"
    
    start_time = time.time()
    timeout = settings.LEONARDO_GENERATION_TIMEOUT
    poll_interval = settings.LEONARDO_POLL_INTERVAL
    
    logger.debug(f"Polling generation status: {generation_id}")
    
    while True:
        try:
            response = requests.get(
                url,
                headers=_api_headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            status = data.get("generations_by_pk", {}).get("status")
            
            if status == "COMPLETE":
                # Get image URL
                generations = data.get("generations_by_pk", {}).get("generated_images", [])
                if generations:
                    image_url = generations[0].get("url", "")
                    logger.info(f"Generation complete: {generation_id}")
                    return {
                        "generation_id": generation_id,
                        "status": "complete",
                        "image_url": image_url,
                    }
                else:
                    logger.warning(f"Generation complete but no image URL: {generation_id}")
                    return {
                        "generation_id": generation_id,
                        "status": "complete",
                        "image_url": "",
                    }
            
            elif status == "FAILED":
                logger.error(f"Generation failed: {generation_id}")
                return {
                    "generation_id": generation_id,
                    "status": "failed",
                    "image_url": "",
                }
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Generation timeout: {generation_id}")
                return {
                    "generation_id": generation_id,
                    "status": "timeout",
                    "image_url": "",
                }
            
            # Wait before next poll
            time.sleep(poll_interval)
            
        except requests.RequestException as e:
            logger.error(f"Error polling generation status: {e}")
            # Retry on network errors
            time.sleep(poll_interval)
            continue
        except Exception as e:
            logger.error(f"Unexpected error polling status: {e}")
            raise


def download_generated_image(image_url: str, save_path: str) -> bool:
    """
    Download generated image to local file.
    
    Args:
        image_url: URL of generated image
        save_path: Local file path to save image
        
    Returns:
        True if successful, False otherwise
    """
    if not image_url:
        logger.warning("No image URL provided")
        return False
    
    try:
        logger.debug(f"Downloading image from {image_url} to {save_path}")
        
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Ensure directory exists
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save image
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Image downloaded successfully: {save_path}")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Failed to download image: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {e}")
        return False


def batch_generate_thumbnails(
    video_ideas: List[Dict[str, Any]],
    output_dir: str = None
) -> List[Dict[str, Any]]:
    """
    Orchestrate batch thumbnail generation with retry/rate-limit handling.
    
    Args:
        video_ideas: List of video idea dictionaries
        output_dir: Directory to save thumbnails (defaults to settings.DATA_DIR)
        
    Returns:
        List of thumbnail dictionaries with generation results
    """
    if output_dir is None:
        output_dir = settings.DATA_DIR
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting batch thumbnail generation for {len(video_ideas)} video ideas")
    
    thumbnails = []
    max_retries = settings.MAX_RETRIES
    retry_delay = settings.RETRY_DELAY
    
    for i, idea in enumerate(video_ideas, 1):
        idea_title = idea.get('title', f'idea_{i}')
        prompt = f"Video thumbnail for: {idea_title}"
        
        logger.info(f"Processing {i}/{len(video_ideas)}: {idea_title}")
        
        # Retry logic
        for attempt in range(max_retries):
            try:
                # Generate thumbnail
                generation_result = generate_thumbnail(prompt)
                generation_id = generation_result["generation_id"]
                
                # Poll for completion
                status_result = get_generation_status(generation_id)
                
                if status_result["status"] == "complete" and status_result.get("image_url"):
                    # Download image
                    image_url = status_result["image_url"]
                    filename = f"thumbnail_{generation_id}.png"
                    save_path = output_path / filename
                    
                    if download_generated_image(image_url, str(save_path)):
                        thumbnail = {
                            "video_idea_id": idea.get('title', ''),
                            "generation_id": generation_id,
                            "image_url": image_url,
                            "local_path": str(save_path),
                            "prompt": prompt,
                            "status": "success",
                            "generated_at": datetime.utcnow().isoformat(),
                        }
                        thumbnails.append(thumbnail)
                        logger.info(f"Successfully generated thumbnail {i}/{len(video_ideas)}")
                        break
                    else:
                        logger.warning(f"Failed to download image for {idea_title}")
                else:
                    logger.warning(f"Generation failed for {idea_title}: {status_result.get('status')}")
                
                # If we get here, generation failed - retry if attempts remain
                if attempt < max_retries - 1:
                    logger.info(f"Retrying {idea_title} (attempt {attempt + 2}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    thumbnail = {
                        "video_idea_id": idea.get('title', ''),
                        "generation_id": generation_id if 'generation_id' in locals() else "",
                        "image_url": "",
                        "local_path": "",
                        "prompt": prompt,
                        "status": "failed",
                        "generated_at": datetime.utcnow().isoformat(),
                    }
                    thumbnails.append(thumbnail)
                    logger.error(f"Failed to generate thumbnail for {idea_title} after {max_retries} attempts")
                
            except Exception as e:
                logger.error(f"Error generating thumbnail for {idea_title} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    thumbnail = {
                        "video_idea_id": idea.get('title', ''),
                        "generation_id": "",
                        "image_url": "",
                        "local_path": "",
                        "prompt": prompt,
                        "status": "error",
                        "error": str(e),
                        "generated_at": datetime.utcnow().isoformat(),
                    }
                    thumbnails.append(thumbnail)
        
        # Rate limiting: small delay between requests
        if i < len(video_ideas):
            time.sleep(1)
    
    logger.info(f"Batch generation complete: {len([t for t in thumbnails if t['status'] == 'success'])}/{len(video_ideas)} successful")
    return thumbnails


def main():
    """Main execution function for command-line invocation."""
    import sys
    
    try:
        logger.info("Starting thumbnail generation process")
        
        # Initialize client
        initialize_leonardo_client()
        
        # Load video ideas from file
        input_file = settings.VIDEO_IDEAS_FILE
        logger.info(f"Loading video ideas from {input_file}")
        
        try:
            data = load_json(input_file)
            video_ideas = data.get('items', [])
        except FileNotFoundError:
            logger.error(f"Input file not found: {input_file}")
            return 1
        
        if not video_ideas:
            logger.warning("No video ideas to process")
            return 0
        
        # Generate thumbnails
        thumbnails = batch_generate_thumbnails(video_ideas)
        
        # Save thumbnails metadata
        output_file = settings.THUMBNAILS_FILE
        output_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_thumbnails': len(thumbnails),
            'successful': len([t for t in thumbnails if t['status'] == 'success']),
            'items': thumbnails,
        }
        save_json(output_data, output_file)
        
        logger.info("Thumbnail generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)

