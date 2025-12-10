"""
Leonardo AI API client for thumbnail generation.

Handles image generation, status polling, and batch processing for video thumbnails.
"""

import time
import os
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import settings
from app.scripts.data_manager import load_json, save_json


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
    
    # Log API key status (masked for security)
    api_key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    # logger.info(f"Leonardo API key loaded (preview: {api_key_preview}, length: {len(api_key)})")
    
    _api_key = api_key
    _api_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # logger.info("Leonardo API client initialized")


def generate_thumbnail(prompt: str, model_id: str = None, use_alchemy: bool = None, model_type: str = "photoreal", tags: List[str] = None) -> Dict[str, Any]:
    """
    Generate thumbnail image via Leonardo API.
    
    Args:
        prompt: Text prompt for image generation
        model_id: Model ID to use (defaults to settings.LEONARDO_DEFAULT_MODEL_ID)
        use_alchemy: Whether to use Alchemy enhancement (defaults to settings.LEONARDO_USE_ALCHEMY)
        model_type: Model type - "photoreal" or "fluxdev" (defaults to "photoreal")
        
    Returns:
        Dictionary with generation_id and status
    """
    if _api_headers is None:
        initialize_leonardo_client()
    
    # Select model based on type
    if model_id is None:
        if model_type == "fluxdev":
            model_id = settings.LEONARDO_FLUXDEV_MODEL_ID
        else:
            model_id = settings.LEONARDO_PHOTOREAL_MODEL_ID
    
    if use_alchemy is None:
        use_alchemy = settings.LEONARDO_USE_ALCHEMY
    
    url = f"{settings.LEONARDO_API_BASE_URL}/generations"
    
    # Build enhanced prompt using the specified format
    # Incorporate visual tags if available (strictly use only visual_tags, not RSS tags)
    tags_section = ""
    if tags and len(tags) > 0:
        # Use up to 3 visual tags
        tag_list = tags[:3]
        tags_section = f"\n\nVisual theme focus: {', '.join(tag_list)}.\n\n"
    
    enhanced_prompt = (
        f"High-end AI technology artwork in a dark futuristic theme. "
        f"\n\n"
        f"Deep space black (#0f1419) background with vibrant orange (#ff6b35) accent lighting. "
        f"\n\n"
        f"Sleek cinematic composition with glowing neural networks, holographic UI panels, data streams, and abstract tech shapes. "
        f"\n\n"
        f"Ultra-clean, minimal, professional, high-tech visual identity consistent with an AI news platform."
        f"{tags_section}"
        f"Hyper-detailed, sharp, 4K render, cinematic lighting, volumetric glow, depth-of-field, "
        f"symmetry, centered focal point, smooth gradients, polished futuristic UI design. "
        f"\n\n"
        f"STRICT: no text, no words, no letters, no symbols, no logos. "
        f"\n\n"
        f"Pure imagery only."
    )
    
    payload = {
        "prompt": enhanced_prompt,
        "width": settings.LEONARDO_THUMBNAIL_WIDTH,
        "height": settings.LEONARDO_THUMBNAIL_HEIGHT,
        "num_images": 1,  # Generate one image
    }
    
    # Add Alchemy parameters if enabled
    if use_alchemy:
        payload["alchemy"] = True
        payload["presetStyle"] = settings.LEONARDO_PRESET_STYLE
        if model_type == "photoreal":
            # PhotoReal mode: don't include modelId, use photoReal instead
            payload["photoReal"] = True
            payload["photoRealStrength"] = settings.LEONARDO_PHOTOREAL_STRENGTH
        else:
            # For non-PhotoReal models (e.g., FluxDev), include modelId
            payload["modelId"] = model_id
        payload["enhancePrompt"] = settings.LEONARDO_ENHANCE_PROMPT
    else:
        # If Alchemy is disabled, include modelId for all model types
        payload["modelId"] = model_id
    
    # logger.debug(f"Generating thumbnail with prompt: {prompt[:50]}...")
    
    try:
        # logger.info(f"Request URL: {url}")
        # logger.info(f"Request payload: {payload}")
        # Log Authorization header (masked)
        auth_header_preview = _api_headers.get("Authorization", "")[:20] + "..." if _api_headers.get("Authorization") else "None"
        # logger.info(f"Authorization header: {auth_header_preview}")
        
        response = requests.post(
            url,
            headers=_api_headers,
            json=payload,
            timeout=30
        )
        
        # Log response details for debugging
        # logger.info(f"Response status: {response.status_code}")
        
        # Try to get response body even on error
        try:
            response_data = response.json()
            # logger.info(f"Response body: {response_data}")
        except:
            # logger.info(f"Response text: {response.text[:500]}")
        
        response.raise_for_status()
        
        data = response.json()
        generation_id = data.get("sdGenerationJob", {}).get("generationId")
        
        if not generation_id:
            # logger.error(f"No generation ID in response: {data}")
            raise ValueError("No generation ID returned from API")
        
        # logger.info(f"Thumbnail generation started: {generation_id}")
        
        return {
            "generation_id": generation_id,
            "status": "pending",
            "prompt": prompt,
            "model_id": model_id,
        }
        
    except requests.HTTPError as e:
        error_msg = f"HTTP {e.response.status_code}"
        try:
            error_body = e.response.json()
            error_msg += f": {error_body}"
        except:
            error_msg += f": {e.response.text[:200]}"
        # logger.error(f"Failed to generate thumbnail: {error_msg}")
        raise Exception(f"Leonardo API error: {error_msg}") from e
    except requests.RequestException as e:
        # logger.error(f"Failed to generate thumbnail: {e}")
        raise
    except Exception as e:
        # logger.error(f"Unexpected error generating thumbnail: {e}")
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
    
    # logger.debug(f"Polling generation status: {generation_id}")
    
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
                    # logger.info(f"Generation complete: {generation_id}")
                    return {
                        "generation_id": generation_id,
                        "status": "complete",
                        "image_url": image_url,
                    }
                else:
                    # logger.warning(f"Generation complete but no image URL: {generation_id}")
                    return {
                        "generation_id": generation_id,
                        "status": "complete",
                        "image_url": "",
                    }
            
            elif status == "FAILED":
                # logger.error(f"Generation failed: {generation_id}")
                return {
                    "generation_id": generation_id,
                    "status": "failed",
                    "image_url": "",
                }
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                # logger.error(f"Generation timeout: {generation_id}")
                return {
                    "generation_id": generation_id,
                    "status": "timeout",
                    "image_url": "",
                }
            
            # Wait before next poll
            time.sleep(poll_interval)
            
        except requests.RequestException as e:
            # logger.error(f"Error polling generation status: {e}")
            # Retry on network errors
            time.sleep(poll_interval)
            continue
        except Exception as e:
            # logger.error(f"Unexpected error polling status: {e}")
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
        # logger.warning("No image URL provided")
        return False
    
    try:
        # logger.debug(f"Downloading image from {image_url} to {save_path}")
        
        response = requests.get(image_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Ensure directory exists
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save image
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # logger.info(f"Image downloaded successfully: {save_path}")
        return True
        
    except requests.RequestException as e:
        # logger.error(f"Failed to download image: {e}")
        return False
    except Exception as e:
        # logger.error(f"Unexpected error downloading image: {e}")
        return False


def batch_generate_thumbnails(
    video_ideas: List[Dict[str, Any]],
    output_dir: str = None,
    model_type: str = "photoreal",
    use_alchemy: bool = True
) -> List[Dict[str, Any]]:
    """
    Orchestrate batch thumbnail generation with retry/rate-limit handling.
    
    Args:
        video_ideas: List of video idea dictionaries
        output_dir: Directory to save thumbnails (defaults to settings.DATA_DIR)
        model_type: Model type to use - "photoreal" or "fluxdev" (default: "photoreal")
        use_alchemy: Whether to use Alchemy enhancement (default: True)
        
    Returns:
        List of thumbnail dictionaries with generation results
    """
    if output_dir is None:
        output_dir = settings.DATA_DIR
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # logger.info(f"Starting batch thumbnail generation for {len(video_ideas)} video ideas")
    
    thumbnails = []
    max_retries = settings.MAX_RETRIES
    retry_delay = settings.RETRY_DELAY
    
    for i, idea in enumerate(video_ideas, 1):
        idea_title = idea.get('title', f'idea_{i}')
        prompt = f"Video thumbnail for: {idea_title}"
        
        # Get visual_tags (for Leonardo image generation) - these are the categorized visual tags
        visual_tags = idea.get('visual_tags', [])
        if not visual_tags:
            # Fallback: try to get from original article reference
            visual_tags = idea.get('original_visual_tags', [])
        
        # Use visual_tags for image generation (not RSS tags)
        tags = visual_tags
        
        # logger.info(f"Processing {i}/{len(video_ideas)}: {idea_title} (visual tags: {', '.join(tags[:3]) if tags else 'none'})")
        
        # Retry logic
        for attempt in range(max_retries):
            try:
                # Generate thumbnail with specified model and alchemy, including tags
                generation_result = generate_thumbnail(
                    prompt, 
                    model_id=None,  # Will use default based on model_type
                    use_alchemy=use_alchemy,
                    model_type=model_type,
                    tags=tags
                )
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
                        # logger.info(f"Successfully generated thumbnail {i}/{len(video_ideas)}")
                        break
                    else:
                        # logger.warning(f"Failed to download image for {idea_title}")
                else:
                    # logger.warning(f"Generation failed for {idea_title}: {status_result.get('status')}")
                
                # If we get here, generation failed - retry if attempts remain
                if attempt < max_retries - 1:
                    # logger.info(f"Retrying {idea_title} (attempt {attempt + 2}/{max_retries})")
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
                    # logger.error(f"Failed to generate thumbnail for {idea_title} after {max_retries} attempts")
                
            except Exception as e:
                # logger.error(f"Error generating thumbnail for {idea_title} (attempt {attempt + 1}): {e}")
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
    
    # logger.info(f"Batch generation complete: {len([t for t in thumbnails if t['status'] == 'success'])}/{len(video_ideas)} successful")
    return thumbnails


def main():
    """Main execution function for command-line invocation."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate thumbnails for video ideas')
    parser.add_argument('--input', type=str, help='Input file path (default: video_ideas.json)')
    parser.add_argument('--limit', type=int, help='Limit number of video ideas to process')
    args = parser.parse_args()
    
    try:
        # logger.info("Starting thumbnail generation process")
        
        # Initialize client
        initialize_leonardo_client()
        
        # Load video ideas from file
        if args.input:
            input_file = args.input
        else:
            input_file = settings.VIDEO_IDEAS_FILE
        # logger.info(f"Loading video ideas from {input_file}")
        
        try:
            data = load_json(input_file)
            video_ideas = data.get('items', [])
            
            # Apply limit if specified
            if args.limit and args.limit > 0:
                original_count = len(video_ideas)
                video_ideas = video_ideas[:args.limit]
                # logger.info(f"Limited video ideas from {original_count} to {len(video_ideas)}")
        except FileNotFoundError:
            # logger.error(f"Input file not found: {input_file}")
            return 1
        
        if not video_ideas:
            # logger.warning("No video ideas to process")
            return 0
        
        # Generate thumbnails with Photoreal model and Alchemy
        # Try Photoreal first, then FluxDev as fallback
        model_type = os.getenv("LEONARDO_MODEL_TYPE", "photoreal")  # "photoreal" or "fluxdev"
        thumbnails = batch_generate_thumbnails(video_ideas, model_type=model_type, use_alchemy=True)
        
        # Save thumbnails metadata
        output_file = settings.THUMBNAILS_FILE
        output_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_thumbnails': len(thumbnails),
            'successful': len([t for t in thumbnails if t['status'] == 'success']),
            'items': thumbnails,
        }
        save_json(output_data, output_file)
        
        # logger.info("Thumbnail generation completed successfully")
        return 0
        
    except Exception as e:
        # logger.error(f"Thumbnail generation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    """Command-line execution."""
    import sys
    exit_code = main()
    sys.exit(exit_code)

