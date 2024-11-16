from typing import Optional, Dict, Any
from datetime import timedelta
import json
import io
import base64
import logging
from PIL import Image
from core.redis_manager import RedisManager

class ImageProcessor:
    """
    Procesor pentru imagini care gestionează procesarea asincronă a imaginilor
    și stocarea lor în cache.
    """
    
    def __init__(self, redis_manager: RedisManager, s3_manager: Any, rabbitmq_manager: Any):
        self.redis = redis_manager
        self.s3_manager = s3_manager
        self.rabbitmq_manager = rabbitmq_manager
        self.image_prefix = "exercise:image:"
        self.thumbnail_size = (128, 128)
        self.cache_ttl = timedelta(hours=12)
        self.bucket_name = 'proveit-exercises-directories'
        self.logger = logging.getLogger(__name__)
        
    def start_processing(self):
        """
        Începe procesarea imaginilor din coadă
        """
        try:
            def callback(ch, method, properties, body):
                try:
                    self.process_image_message(body)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    # Requeue message if needed
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            self.rabbitmq_manager.channel.basic_qos(prefetch_count=1)
            self.rabbitmq_manager.consume(queue_name="image_processing", callback=callback, auto_ack=False)
            self.logger.info("Started image processing worker")
            
        except Exception as e:
            self.logger.error(f"Error starting image processing worker: {e}")
            
        finally:
            self.rabbitmq_manager.close()

    def process_image_message(self, message_body: bytes) -> None:
        """
        Procesează un mesaj pentru o imagine primit de la RabbitMQ.
        
        Args:
            message_body: Conținutul mesajului în format bytes
        """
        try:
            # Parsează mesajul
            data = json.loads(message_body)
            exercise_id = data['exercise_id']
            image_url = data['image_url']
            
            self.logger.info(f"Starting image processing for exercise {exercise_id}")
            
            # Verifică dacă imaginea există deja în cache
            if self.get_cached_thumbnail(exercise_id):
                self.logger.info(f"Thumbnail already exists for exercise {exercise_id}")
                return
                
            # Procesează imaginea
            thumbnail_uri = self._process_exercise_image(exercise_id, image_url)
            if thumbnail_uri:
                self._update_exercise_cache(exercise_id, thumbnail_uri)
                self.logger.info(f"Successfully processed image for exercise {exercise_id}")
                
        except Exception as e:
            self.logger.error(f"Error processing image message for exercise {exercise_id}: {e}")
            
    def _process_exercise_image(self, exercise_id: str, image_url: str) -> Optional[str]:
        """
        Procesează imaginea unui exercițiu.
        
        Args:
            exercise_id: ID-ul exercițiului
            image_url: URL-ul imaginii din S3
            
        Returns:
            URI-ul thumbnail-ului în format base64 sau None în caz de eroare
        """
        try:
            # Extrage path-ul din URL
            path_parts = image_url.split('?')[0].split(f'{self.bucket_name}.s3.amazonaws.com/')[1]
            
            # Obține imaginea din S3
            image_data = self.s3_manager.get_object(self.bucket_name, path_parts)
            if not image_data:
                self.logger.error(f"Could not get image data from S3 for exercise {exercise_id}")
                return None
                
            # Procesează imaginea
            return self._create_thumbnail(exercise_id, image_data)
                
        except Exception as e:
            self.logger.error(f"Error processing image for exercise {exercise_id}: {e}")
            return None
            
    def _create_thumbnail(self, exercise_id: str, image_data: bytes) -> Optional[str]:
        """
        Creează un thumbnail din datele binare ale imaginii.
        
        Args:
            exercise_id: ID-ul exercițiului
            image_data: Datele binare ale imaginii
            
        Returns:
            URI-ul thumbnail-ului în format base64 sau None în caz de eroare
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convertește la RGB dacă e necesar
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Redimensionează imaginea
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Salvează ca JPEG optimizat
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                image_data = buffer.getvalue()
                
                # Convertește la base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                print(exercise_id)
                return f"data:image/jpeg;base64,{image_base64}"
                
        except Exception as e:
            self.logger.error(f"Error creating thumbnail for exercise {exercise_id}: {e}")
            return None
            
    def _update_exercise_cache(self, exercise_id: str, thumbnail_uri: str) -> None:
        """
        Actualizează cache-ul cu noul thumbnail.
        
        Args:
            exercise_id: ID-ul exercițiului
            thumbnail_uri: URI-ul thumbnail-ului
        """
        try:
            # Salvează thumbnail-ul individual
            self.redis.set(
                f"{self.image_prefix}{exercise_id}",
                thumbnail_uri,
                expires_in=self.cache_ttl
            )
            
            # Actualizează exercițiul în lista completă
            exercises = self.redis.get("exercises:all")
            if exercises:
                for exercise in exercises:
                    if exercise['id'] == exercise_id:
                        if 'image' not in exercise:
                            exercise['image'] = {}
                        exercise['image']['thumbnail'] = thumbnail_uri
                        break
                
                self.redis.set("exercises:all", exercises, expires_in=self.cache_ttl)
                
        except Exception as e:
            self.logger.error(f"Error updating cache for exercise {exercise_id}: {e}")
            
    def get_cached_thumbnail(self, exercise_id: str) -> Optional[str]:
        """
        Obține un thumbnail din cache.
        
        Args:
            exercise_id: ID-ul exercițiului
            
        Returns:
            URI-ul thumbnail-ului sau None dacă nu există
        """
        try:
            return self.redis.get(f"{self.image_prefix}{exercise_id}")
        except Exception as e:
            self.logger.error(f"Error getting cached thumbnail for exercise {exercise_id}: {e}")
            return None
            
    def clear_thumbnail_cache(self) -> None:
        """Șterge toate thumbnail-urile din cache"""
        try:
            pattern = f"{self.image_prefix}*"
            cleared = self.redis.clear_cache(pattern)
            self.logger.info(f"Cleared {cleared} thumbnails from cache")
        except Exception as e:
            self.logger.error(f"Error clearing thumbnail cache: {e}")