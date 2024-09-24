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
