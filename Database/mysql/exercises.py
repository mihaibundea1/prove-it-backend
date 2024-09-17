from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

def get_db():
    return current_app.mysql_db

def fetch_exercises():
    try:
        query = "SELECT * FROM exercises"
        result = get_db().execute_query(query)
        
        if result:
            # Assuming the result is a list of tuples and columns are known
            columns = ["id", "name", "duration", "video_url", "image_url", "category"]  # Adjust based on actual column names
            
            # Convert the list of tuples to a list of dictionaries
            serialized_result = [dict(zip(columns, row)) for row in result]
            
            print(f'{serialized_result} is serialized_result')  # For debugging purposes
            return serialized_result
        else:
            return []
    except SQLAlchemyError as e:
        print(f"Error in fetch_exercises: {e}")
        return []
