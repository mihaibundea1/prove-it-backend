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
            bucket_name = 'proveit-exercises-directories'
            
            for row in result:
                # Parse images JSON string to list
                images = json.loads(row['images']) if row['images'] else []
                
                # Keep original S3 paths
                image_urls = []
                for image_path in images:
                    if isinstance(image_path, bytes):
                        image_path = image_path.decode('utf-8')
                    if isinstance(image_path, str) and image_path.startswith(f's3://{bucket_name}/'):
                        image_urls.append(image_path)
                
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
                        'uri': image_urls
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
    try:
        current_app.logger.info(f"Attempting to fetch details for exercise: {exercise_id}")
        
        query = """
            SELECT name, `force`, level, mechanic, equipment, category,
                   primary_muscles, secondary_muscles, instructions, images
            FROM exercises 
            WHERE id = %s
        """
        
        current_app.logger.debug(f"Query: {query}")
        current_app.logger.debug(f"Parameters: {exercise_id}")
        
        db = get_db()
        result = db.execute_query(query, (exercise_id,))
        
        # Log the result type and content
        current_app.logger.debug(f"Query result type: {type(result)}")
        current_app.logger.debug(f"Query result content: {result}")
        
        if result and len(result) > 0:
            row = result[0]
            current_app.logger.debug(f"Row type: {type(row)}")
            current_app.logger.debug(f"Row content: {row}")
            
            try:
                # Handle both sequence and mapping types
                if isinstance(row, (tuple, list)):
                    exercise_dict = {
                        'id': exercise_id,
                        'name': row[0],
                        'force': row[1],
                        'level': row[2],
                        'mechanic': row[3],
                        'equipment': row[4],
                        'category': row[5],
                        'primary_muscles': json.loads(row[6]) if row[6] else [],
                        'secondary_muscles': json.loads(row[7]) if row[7] else [],
                        'instructions': json.loads(row[8]) if row[8] else [],
                        'images': []
                    }
                else:  # Assuming it's a dictionary-like object
                    exercise_dict = {
                        'id': exercise_id,
                        'name': row['name'],
                        'force': row['force'],
                        'level': row['level'],
                        'mechanic': row['mechanic'],
                        'equipment': row['equipment'],
                        'category': row['category'],
                        'primary_muscles': json.loads(row['primary_muscles']) if row['primary_muscles'] else [],
                        'secondary_muscles': json.loads(row['secondary_muscles']) if row['secondary_muscles'] else [],
                        'instructions': json.loads(row['instructions']) if row['instructions'] else [],
                        'images': []
                    }
                
                current_app.logger.debug("Successfully created exercise dictionary")
                
                # Process images from S3 URLs
                try:
                    images_data = row['images'] if isinstance(row, dict) else row[9]
                    image_urls = json.loads(images_data) if images_data else []
                    current_app.logger.debug(f"Parsed image URLs: {image_urls}")
                    
                    if isinstance(image_urls, list):
                        s3_manager = current_app.s3_manager
                        bucket_name = 'proveit-exercises-directories'
                        
                        for image_url in image_urls:
                            if image_url and 's3://' in image_url:
                                try:
                                    object_key = image_url.split(f's3://{bucket_name}/')[1]
                                    current_app.logger.debug(f"Processing object key: {object_key}")
                                    
                                    presigned_url = s3_manager.generate_presigned_url(bucket_name, object_key)
                                    if presigned_url:
                                        exercise_dict['images'].append(presigned_url)
                                        current_app.logger.debug(f"Added presigned URL for {object_key}")
                                except Exception as e:
                                    current_app.logger.error(f"Error generating presigned URL for {image_url}: {str(e)}")
                                    continue
                    
                    current_app.logger.info(f"Successfully processed images for exercise {exercise_id}")
                except json.JSONDecodeError as e:
                    current_app.logger.error(f"JSON parsing error for images: {str(e)}")
                except Exception as e:
                    current_app.logger.error(f"Error processing images: {str(e)}")
                
                return exercise_dict
            except Exception as e:
                current_app.logger.error(f"Error creating exercise dictionary: {str(e)}")
                current_app.logger.error(f"Row data that caused error: {row}")
                raise
                
        else:
            current_app.logger.warning(f"No details found for exercise {exercise_id}")
            return None
            
    except Exception as e:
        current_app.logger.error(f"Unexpected error in fetch_exercise_details: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return None