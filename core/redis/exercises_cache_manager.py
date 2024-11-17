from typing import List, Dict, Optional
from datetime import timedelta
from core.redis_manager import RedisManager
import logging
from Database.mysql.exercises import fetch_all_exercises
from core.rabbitmq_manager import RabbitMQManager

class ExercisesCacheManager:
    def __init__(self):
        self.redis = RedisManager()
        self.rabbitmq = RabbitMQManager()
        self.exercises_key = "exercises:all"
        self.image_prefix = "exercise:image:"
        self.cache_ttl = timedelta(hours=168)
        self.queue_name = "image_processing_queue"
        self.logger = logging.getLogger(__name__)

    def check_missing_thumbnails(self, exercises: List[Dict]) -> bool:
        """
        Check if any exercises are missing thumbnails and queue them for processing if needed
        Returns True if any exercises need processing
        """
        try:
            missing_thumbnails = False
            for exercise in exercises:
                if (
                    'image' in exercise 
                    and exercise.get('image', {}).get('uri') 
                    and exercise.get('image', {}).get('thumbnail') is None
                ):
                    missing_thumbnails = True
                    break
            
            if missing_thumbnails:
                self.logger.info("Found exercises missing thumbnails, queuing for processing")
                self.rabbitmq.publish(
                    queue_name=self.queue_name,
                    message={'action': 'process_exercises', 'count': len(exercises)},
                    persistent=True
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking thumbnails: {e}", exc_info=True)
            return False
        
    def set_exercises(self, exercises: List[Dict]) -> bool:
        """Set exercises in cache and queue them for image processing"""
        try:
            self.logger.info(f"Setting {len(exercises)} exercises in cache")
            
            # Initialize thumbnails to None if not present
            for exercise in exercises:
                if 'image' in exercise:
                    exercise['image']['thumbnail'] = None
                    
            # Save to Redis
            success = self.redis.set(
                key=self.exercises_key,
                value=exercises,
                expires_in=self.cache_ttl  # Changed from ex to expires_in
            )
            
            if not success:
                self.logger.error("Failed to save exercises to Redis")
                return False
            
            # Queue image processing
            self.rabbitmq.publish(
                queue_name=self.queue_name,
                message={'action': 'process_exercises', 'count': len(exercises)},
                persistent=True
            )
            
            self.logger.info(f"Successfully cached {len(exercises)} exercises and queued for processing")
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting exercises in cache: {e}", exc_info=True)
            return False

    def initialize_cache(self) -> int:
        try:
            self.logger.info("Starting cache initialization...")
            exercises = fetch_all_exercises(page=1, limit=1000)
            
            if not exercises:
                self.logger.warning("No exercises returned from database")
                return 0
                
            if self.set_exercises(exercises):
                return len(exercises)
            return 0
            
        except Exception as e:
            self.logger.error(f"Cache initialization failed: {e}", exc_info=True)
            return 0

    def get_exercises(self) -> Optional[List[Dict]]:
        """Get exercises from cache"""
        try:
            exercises = self.redis.get(self.exercises_key)
            self.logger.info(f"Retrieved {len(exercises) if exercises else 0} exercises from cache")
            return exercises
        except Exception as e:
            self.logger.error(f"Error retrieving exercises: {e}")
            return None

    def clear_cache(self) -> int:
        """Clear the cache"""
        try:
            patterns = [
                self.exercises_key,
                f"{self.image_prefix}*"
            ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = self.redis.clear_cache(pattern)
                total_cleared += cleared
                
            self.logger.info(f"Cleared {total_cleared} cache entries")
            return total_cleared
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return 0
            
    def __del__(self):
        """Cleanup when object is deleted"""
        if hasattr(self, 'rabbitmq'):
            self.rabbitmq.close()