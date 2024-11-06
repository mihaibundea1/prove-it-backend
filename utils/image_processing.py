# utils/image_processing.py

from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def resize_and_cache_image(s3_manager, redis_manager, bucket_name, image_key, size=(150, 150)):
    """
    Resize an image from S3 and cache it in Redis
    
    Args:
        s3_manager: Instance of S3 manager
        redis_manager: Instance of RedisManager
        bucket_name: S3 bucket name
        image_key: Key of the image in S3
        size: Tuple of (width, height) for resizing
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache_key = f"image:{image_key}:{size[0]}x{size[1]}"
        
        # Check if image is already cached
        cached_image = redis_manager.get(cache_key, deserialize=False)
        if cached_image:
            return True
            
        # Get image from S3
        image_data = s3_manager.get_object(bucket_name, image_key)
        if not image_data:
            logger.error(f"Could not get image {image_key} from S3")
            return False
            
        # Resize image
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail(size)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        resized_image = buffer.getvalue()
        
        # Cache in Redis (24 hours)
        redis_manager.set(cache_key, resized_image, expires_in=86400)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing image {image_key}: {e}")
        return False