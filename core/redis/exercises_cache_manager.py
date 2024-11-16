from typing import List, Dict, Optional
from datetime import timedelta
from core.redis_manager import RedisManager
from PIL import Image
import io
import base64
import json
import logging
from Database.mysql.exercises import fetch_all_exercises

class ExercisesCacheManager:
    def __init__(self):
        self.redis = RedisManager()
        self.exercises_key = "exercises:all"
        self.image_prefix = "exercise:image:"
        self.cache_ttl = timedelta(hours=12)
        self.thumbnail_size = (128, 128)
        self.bucket_name = 'proveit-exercises-directories'
        self.logger = logging.getLogger(__name__)
        
    def initialize_cache(self, s3_manager) -> int:
        try:
            print("Starting cache initialization...")
            exercises = fetch_all_exercises(page=1, limit=1000)
            
            if not exercises:
                print("No exercises returned from fetch_all_exercises")
                return 0
                
            print(f"Found {len(exercises)} exercises")
            
            processed_count = 0
            for exercise in exercises:
                try:
                    if not exercise.get('id'):
                        continue
                    
                    print(f"\nProcessing exercise {exercise['id']}")
                    
                    # Preluăm path-ul imaginii din S3
                    if 'image' in exercise and 'uri' in exercise['image']:
                        # Extragem path-ul din URL-ul S3
                        image_url = exercise['image']['uri']
                        if 'proveit-exercises-directories.s3' in image_url:
                            # Extragem path-ul relativ din URL
                            path_parts = image_url.split('?')[0].split('proveit-exercises-directories.s3.amazonaws.com/')[1]
                            
                            print(f"Getting image from S3: {path_parts}")
                            
                            # Obținem imaginea direct din S3
                            image_data = s3_manager.get_object(self.bucket_name, path_parts)
                            if image_data:
                                # Procesăm și salvăm thumbnail-ul
                                thumbnail = self.process_image(exercise['id'], image_data)
                                if thumbnail:
                                    exercise['image']['thumbnail'] = thumbnail
                                    processed_count += 1
                                    print(f"Successfully processed image for exercise {exercise['id']}")
                    
                except Exception as e:
                    print(f"Error processing exercise {exercise.get('id')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
            print(f"\nSaving {len(exercises)} exercises to cache")
            self.redis.set(self.exercises_key, exercises, expires_in=self.cache_ttl)
            print(f"Successfully initialized cache with {processed_count} processed images")
            return processed_count
            
        except Exception as e:
            print(f"Cache initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return 0
            
    def process_image(self, exercise_id: str, image_data: bytes) -> Optional[str]:
        """
        Procesează datele binare ale imaginii și creează un thumbnail
        """
        try:
            cache_key = f"{self.image_prefix}{exercise_id}"
            
            # Verifică cache-ul
            cached_image = self.redis.get(cache_key)
            if cached_image:
                return cached_image

            # Procesează imaginea
            with Image.open(io.BytesIO(image_data)) as img:
                print(f"Processing image for {exercise_id}. Original size: {img.size}")
                
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Redimensionează
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Salvează ca JPEG optimizat
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                image_data = buffer.getvalue()
                print(f"Thumbnail created. Size: {len(image_data)} bytes")
                
                # Convertește la base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                thumbnail_uri = f"data:image/jpeg;base64,{image_base64}"
                
                # Salvează în cache
                self.redis.set(cache_key, thumbnail_uri, expires_in=self.cache_ttl)
                
                print(f"Successfully cached thumbnail for exercise {exercise_id}")
                return thumbnail_uri
                
        except Exception as e:
            print(f"Error processing image for exercise {exercise_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def get_exercises(self) -> Optional[List[Dict]]:
        """
        Obține exercițiile din cache
        """
        exercises = self.redis.get(self.exercises_key)
        print(f"Retrieved {len(exercises) if exercises else 0} exercises from cache")
        return exercises

    def clear_cache(self):
        """
        Șterge tot cache-ul de exerciții
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
                
            print(f"Cleared {total_cleared} cache entries")
            return total_cleared
            
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return 0