from flask import Blueprint, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError
import base64

exercises_bp = Blueprint('exercises', __name__)

def get_db():
    return current_app.mysql_db

def fetch_exercise_groups():
    try:
        query = "SELECT id, name, image FROM exercise_groups"
        result = get_db().execute_query(query)
        
        current_app.logger.debug(f"Fetched {len(result)} exercise groups from the database.")
        
        if result:
            columns = ["id", "name", "image"]
            serialized_result = []
            
            for row in result:
                group_dict = dict(zip(columns, row))
                                
                # Convert BLOB to base64 encoded string
                if group_dict['image'] is not None:
                    image_size = len(group_dict['image'])
                    
                    image_base64 = base64.b64encode(group_dict['image']).decode('utf-8')
                    group_dict['image_data'] = f"data:image/jpeg;base64,{image_base64}"
                    
                else:
                    current_app.logger.debug(f"No image found for group {group_dict['id']}")
                    group_dict['image_data'] = None
                
                # Remove the original BLOB data
                del group_dict['image']
                
                serialized_result.append(group_dict)
            
            current_app.logger.debug(f"Processed {len(serialized_result)} exercise groups.")
            return serialized_result
        else:
            current_app.logger.debug("No exercise groups found in the database.")
            return []
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in fetch_exercise_groups: {e}")
        return []

def fetch_exercises_by_group(group_id, limit, offset):
    try:
        print(1)

        query = """
        SELECT exercise_id, exercise_name, image_path, image
        FROM exercise_primary_muscles
        WHERE muscle_group_id = """ + str(group_id) +"""
        LIMIT """  + str(limit) + """ OFFSET  """ + str(offset) + """ """
        print(2)
        print(query)

        result = get_db().execute_query(query)
        
        print(3)

        current_app.logger.debug(f"Fetched exercises for group {group_id} (limit: {limit}, offset: {offset})")
        
        if result:
            print(result)
            serialized_result = []
            for row in result:
                exercise_dict = {
                    'exercise_id': row[0],
                    'exercise_name': row[1],
                    'image_path': row[2],
                }
                
                if row[3]:  # row[3] is the image data
                    image_base64 = base64.b64encode(row[3]).decode('utf-8')
                    exercise_dict['image_data'] = f"data:image/jpeg;base64,{image_base64}"
                else:
                    current_app.logger.debug(f"No image found for exercise {row[0]}")
                    exercise_dict['image_data'] = None
                
                serialized_result.append(exercise_dict)
            
            current_app.logger.debug(f"Processed {len(serialized_result)} exercises for group {group_id}.")
            return serialized_result
        else:
            current_app.logger.debug(f"No exercises found for group {group_id}.")
            return []
    except Exception as e:
        current_app.logger.error(f"Database error in fetch_exercises_by_group: {e}")
        return []