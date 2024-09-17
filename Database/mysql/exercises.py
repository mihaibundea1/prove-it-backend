from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError

exercises_bp = Blueprint('exercises', __name__)

def get_db():
    return current_app.mysql_db

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
            
            return serialized_result
        else:
            return []
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in fetch_exercise_groups: {e}")
        return []