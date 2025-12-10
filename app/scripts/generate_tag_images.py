"""
Generate tag images for AI topics.

Generates one image per AI topic and saves them as numbered files.
These images are reused for articles based on their assigned AI topic tags.
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from app.config import settings
from app.scripts.tag_categorizer import AI_TOPICS
from app.scripts.leonardo_api import (
    initialize_leonardo_client,
    generate_thumbnail,
    get_generation_status,
    download_generated_image
)



def generate_tag_images(output_dir: Path, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Generate images for visual tag categories.
    
    Args:
        output_dir: Directory to save images
        limit: Maximum number of images to generate (default: 30)
        
    Returns:
        List of generated image metadata
    """
    # Initialize Leonardo API client
    initialize_leonardo_client()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all AI topics as tags (flat list, no categories)
    all_tags = []
    for topic in AI_TOPICS:
        all_tags.append({
            "tag": topic,
            "category": "ai",  # All tags are AI-related now
            "category_name": "AI Topics"
        })
    
    # Limit to requested number
    tags_to_generate = all_tags[:limit]
    
    generated_images = []
    
    for i, tag_info in enumerate(tags_to_generate, 1):
        tag = tag_info["tag"]
        category_name = tag_info["category_name"]
        
        # Create prompt for this tag
        prompt = (
            f"High-end AI technology artwork in a dark futuristic theme. "
            f"Deep space black (#0f1419) background with vibrant orange (#ff6b35) accent lighting. "
            f"Sleek cinematic composition with glowing neural networks, holographic UI panels, "
            f"data streams, and abstract tech shapes. Ultra-clean, minimal, professional, "
            f"high-tech visual identity consistent with an AI news platform. "
            f"Visual theme focus: {tag}. "
            f"Hyper-detailed, sharp, 4K render, cinematic lighting, volumetric glow, "
            f"depth-of-field, symmetry, centered focal point, smooth gradients, "
            f"polished futuristic UI design. "
            f"STRICT: no text, no words, no letters, no symbols, no logos. Pure imagery only."
        )
        
        try:
            # Generate thumbnail with PhotoReal model
            generation_result = generate_thumbnail(
                prompt=prompt,
                model_id=None,  # Use default PhotoReal
                use_alchemy=True,
                model_type="photoreal",
                tags=[tag]  # Pass tag for logging
            )
            
            if generation_result and generation_result.get("status") == "pending":
                generation_id = generation_result.get("generation_id")
                
                # Poll for completion
                status_result = get_generation_status(generation_id)
                
                if status_result.get("status") == "complete":
                    image_url = status_result.get("image_url", "")
                    
                    if image_url:
                        # Download and save with numbered filename
                        numbered_filename = f"tag_{i:03d}.png"
                        numbered_path = output_dir / numbered_filename
                        
                        if download_generated_image(image_url, str(numbered_path)):
                            image_metadata = {
                                "tag": tag,
                                "category": tag_info["category"],
                                "category_name": category_name,
                                "image_number": i,
                                "filename": numbered_filename,
                                "local_path": str(numbered_path),
                                "image_url": image_url,
                                "generated_at": datetime.utcnow().isoformat(),
                                "status": "success"
                            }
                            generated_images.append(image_metadata)
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
                
        except Exception as e:
            continue
    
    # Save metadata
    metadata_file = output_dir / "tag_images_metadata.json"
    metadata = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_images": len(generated_images),
        "limit": limit,
        "images": generated_images
    }
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return generated_images


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate tag images for visual tag categories")
    parser.add_argument("--limit", type=int, default=30, help="Maximum number of images to generate")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory for images")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    try:
        generate_tag_images(output_dir, limit=args.limit)
        return 0
    except Exception as e:
        return 1


if __name__ == "__main__":
    import sys
    # Initialize error logging for this script
    from app.scripts.error_logger import initialize_error_logging
    initialize_error_logging()
    
    sys.exit(main())

