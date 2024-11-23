from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
from core.redis_manager import RedisManager
import json
import base64

def get_db():
    return current_app.mysql_db

def get_redis():
    return RedisManager()

def fetch_all_exercises(filters=None, page=1, limit=1000):
    try:
        # Ensure page and limit are integers
        page = int(page) if isinstance(page, str) else page
        limit = int(limit) if isinstance(limit, str) else limit
        offset = (page - 1) * limit
        
        redis_manager = get_redis()
        cache_key = "exercises:all"  # Simplified cache key since we're caching all exercises
        
        # Try to get exercises from cache first
        cached_exercises = redis_manager.get(cache_key)
        if cached_exercises:
            current_app.logger.debug("Retrieved exercises from cache")
            return cached_exercises
            
        # If not in cache, fetch from database
        current_app.logger.info("Cache miss, fetching from database")
        query = """
            SELECT DISTINCT
                e.id,
                e.name,
                e.force,
                e.level,
                e.mechanic,
                e.equipment,
                e.category,
                e.primary_muscles,
                e.secondary_muscles,
                e.instructions,
                e.images,
                e.thumbnail
            FROM exercises e
            WHERE 1=1
            LIMIT %s OFFSET %s
        """
        
        result = get_db().execute_query(query, (limit, offset))
        
        if result:
            exercises = []
            s3_manager = current_app.s3_manager
            bucket_name = 'proveit-exercises-directories'
            
            for row in result:
                # Parse images JSON string to list
                images = json.loads(row['images']) if row['images'] else []
                
                # Generate presigned URLs for images
                image_urls = []
                for image_path in images:
                    if isinstance(image_path, bytes):
                        image_path = image_path.decode('utf-8')
                    if isinstance(image_path, str) and image_path.startswith(f's3://{bucket_name}/'):
                        object_key = image_path.split(f's3://{bucket_name}/')[1]
                        presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                        if presigned_url:
                            image_urls.append(presigned_url)
                
                # Process thumbnail blob
                thumbnail_data = None
                if row['thumbnail']:
                    thumbnail_data = f"data:image/jpeg;strict;base64,{base64.b64encode(row['thumbnail']).decode('utf-8')}"
                
                exercise = {
                    'id': row['id'],
                    'title': row['name'],
                    'force': row['force'],
                    'level': row['level'],
                    'mechanic': row['mechanic'],
                    'equipment': row['equipment'],
                    'category': row['category'],
                    'primary_muscles': json.loads(row['primary_muscles']) if row['primary_muscles'] else [],
                    'secondary_muscles': json.loads(row['secondary_muscles']) if row['secondary_muscles'] else [],
                    'instructions': json.loads(row['instructions']) if row['instructions'] else [],
                    'image': {
                        'uri': image_urls[0] if image_urls else None
                    },
                    'thumbnail': {
                        'uri': thumbnail_data
                    } if thumbnail_data else None
                }
                exercises.append(exercise)
            
            # Cache all exercises
            if exercises:
                redis_manager.set(cache_key, exercises, expires_in=24*3600)
                current_app.logger.debug(f"Cached {len(exercises)} exercises")
            
            return exercises
            
        return []
        
    except Exception as e:
        current_app.logger.error(f"Database error in fetch_all_exercises: {e}")
        return []

def fetch_exercise_groups():
    try:
        query = "SELECT * FROM exercise_groups"
        result = get_db().execute_query(query)
        
        if result:
            columns = ["id", "name", "image_url"]
            serialized_result = [dict(zip(columns, row)) for row in result]
            
            s3_manager = current_app.s3_manager
            bucket_name = 'proveit-exercises-directories'
            
            for group in serialized_result:
                image_url = group.get('image_url')
                print(image_url)
                if image_url:
                    # Extract the S3 object key from the URL
                    object_key = image_url.split(f's3://{bucket_name}/')[1]
                    
                    # Generate a pre-signed URL
                    presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                    
                    if presigned_url:
                        group['image_url'] = presigned_url
                    else:
                        # Handle cases where the pre-signed URL could not be generated
                        group['image_url'] = None
                    print (group['image_url'])
            
            return serialized_result
        else:
            return []
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in fetch_exercise_groups: {e}")
        return []

def fetch_exercises_by_group(group_id, limit, offset):
    redis_manager = get_redis()
    cache_key = f"exercises:group:{group_id}:limit:{limit}:offset:{offset}"
    
    try:
        # Încearcă să obții din cache
        cached_exercises = redis_manager.get(cache_key)
        if cached_exercises:
            current_app.logger.debug(f"Retrieved exercises for group {group_id} from cache")
            # Generează URL-uri noi pentru datele din cache
            s3_manager = current_app.s3_manager
            bucket_name = 'proveit-exercises-directories'
            
            for exercise in cached_exercises:
                image_url = exercise.get('image_url')
                if image_url:
                    object_key = image_url.split(f's3://{bucket_name}/')[1]
                    presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                    exercise['image_url'] = presigned_url if presigned_url else None
                    
            return cached_exercises
            
        query = """
        SELECT e.id, e.name, ep.image_path
        FROM exercises e
        JOIN exercise_primary_muscles ep ON e.id = ep.exercise_id
        WHERE ep.muscle_group_id = %s
        LIMIT %s OFFSET %s
        """
        
        result = get_db().execute_query(query, (group_id, limit, offset))
        
        if result:
            serialized_result = [
                {
                    'exercise_id': row[0],
                    'exercise_name': row[1],
                    'image_url': row[2]
                }
                for row in result
            ]
            
            s3_manager = current_app.s3_manager
            bucket_name = 'proveit-exercises-directories'
            
            for exercise in serialized_result:
                image_url = exercise.get('image_url')
                if image_url:
                    object_key = image_url.split(f's3://{bucket_name}/')[1]
                    presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                    exercise['image_url'] = presigned_url if presigned_url else None
            
            # Salvează în cache pentru 12 ore
            redis_manager.set(cache_key, serialized_result, expires_in=12*3600)
            current_app.logger.debug(f"Cached {len(serialized_result)} exercises for group {group_id}")
            return serialized_result
            
        return []
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in fetch_exercises_by_group: {e}")
        return []
        
    
def fetch_exercise_details(exercise_id):
    redis_manager = get_redis()
    cache_key = f"exercise:details:{exercise_id}"
    
    try:
        # Încearcă să obții din cache
        cached_exercise = redis_manager.get(cache_key)
        if cached_exercise:
            current_app.logger.debug(f"Retrieved exercise {exercise_id} details from cache")
            # Generează URL-uri noi pentru imaginile din cache
            s3_manager = current_app.s3_manager
            bucket_name = 'proveit-exercises-directories'
            
            if isinstance(cached_exercise.get('images'), list):
                updated_images = []
                for image_url in cached_exercise['images']:
                    if image_url:
                        object_key = image_url.split(f's3://{bucket_name}/')[1]
                        presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                        updated_images.append(presigned_url if presigned_url else None)
                cached_exercise['images'] = updated_images
                
            return cached_exercise
        
        query = """
        SELECT 
            name, 
            `force`, 
            level, 
            mechanic, 
            equipment, 
            category,
            primary_muscles,
            secondary_muscles,
            instructions,
            images
        FROM exercises 
        WHERE id = %s
        """
        
        result = get_db().execute_query(query, (exercise_id,))
        
        if result and len(result) > 0:
            row = result[0]
            
            # Parse JSON fields
            try:
                primary_muscles = json.loads(row[6]) if row[6] else []
                secondary_muscles = json.loads(row[7]) if row[7] else []
                instructions = json.loads(row[8]) if row[8] else []
                images = json.loads(row[9]) if row[9] else []
                
                # Generate presigned URLs for images
                s3_manager = current_app.s3_manager
                bucket_name = 'proveit-exercises-directories'
                
                updated_images = []
                for image_url in images:
                    if image_url:
                        object_key = image_url.split(f's3://{bucket_name}/')[1]
                        presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                        updated_images.append(presigned_url if presigned_url else None)
                    else:
                        updated_images.append(None)
                
                images = updated_images
                
            except json.JSONDecodeError as e:
                current_app.logger.error(f"JSON decode error for exercise {exercise_id}: {e}")
                primary_muscles, secondary_muscles, instructions, images = [], [], [], []
            
            exercise_dict = {
                'id': exercise_id,
                'name': row[0],
                'force': row[1],
                'level': row[2],
                'mechanic': row[3],
                'equipment': row[4],
                'category': row[5],
                'primary_muscles': primary_muscles,
                'secondary_muscles': secondary_muscles,
                'instructions': instructions,
                'images': images
            }
            
            # Salvează în cache pentru 24 ore
            redis_manager.set(cache_key, exercise_dict, expires_in=24*3600)
            current_app.logger.debug(f"Cached details for exercise {exercise_id}")
            return exercise_dict
            
        return None
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in fetch_exercise_details: {e}")
        return None