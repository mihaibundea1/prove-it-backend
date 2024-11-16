from typing import List, Dict, Optional
from datetime import timedelta
from core.redis_manager import RedisManager
from core.rabbitmq_manager import RabbitMQManager
from flask import current_app
from Database.mysql.exercises import fetch_all_exercises
import json

class ExercisesCacheManager:
    def __init__(self):
        """Initialize the exercises cache manager"""
        self.redis = RedisManager()
        self.exercises_key = "exercises:all"
        self.image_prefix = "exercise:image:"
        self.cache_ttl = timedelta(hours=12)
        
    def initialize_cache(self, s3_manager) -> int:
        """
        Inițializează cache-ul cu toate exercițiile
        """
        try:
            print("Starting exercises cache initialization...")
            
            # Fetch exercises
            exercises = fetch_all_exercises(limit=1000)  # Get all exercises
            if not exercises:
                print("No exercises found")
                return 0
                
            print(f"Found {len(exercises)} exercises")
            
            # Save to Redis
            self.redis.set(self.exercises_key, exercises, expires_in=self.cache_ttl)
            
            # Queue images for processing if we have an image processor
            if hasattr(current_app, 'image_processor'):
                for exercise in exercises:
                    if exercise.get('image', {}).get('uri'):
                        current_app.image_processor.queue_image_processing(
                            exercise['id'],
                            exercise['image']['uri']
                        )
                print(f"Queued {len(exercises)} images for processing")
            
            return len(exercises)
            
        except Exception as e:
            print(f"Cache initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return 0
            
    def get_exercises(self) -> Optional[List[Dict]]:
        """
        Obține exercițiile din cache
        """
        return self.redis.get(self.exercises_key)
        
    def clear_exercise_cache(self):
        """
        Șterge cache-ul pentru exerciții
        """
        try:
            patterns = [
                self.exercises_key,
                f"{self.image_prefix}*"
            ]
            
            total_cleared = 0
            for pattern in patterns:
                cleared = self.redis.clear_cache(pattern)
                total_cleared += cleared
                
            return total_cleared
            
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return 0