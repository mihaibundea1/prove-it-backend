from flask import Blueprint, jsonify, current_app
from Database.mysql.exercises import fetch_exercise_groups

# Initialize the blueprint
exercises_bp = Blueprint('exercises', __name__)

@exercises_bp.route('/groups', methods=['GET'])
def get_exercise_groups():
    try:
        exercise_groups = fetch_exercise_groups()
        
        current_app.logger.debug(f"Fetched {len(exercise_groups)} exercise groups.")
        
        if exercise_groups:
            # Add debug information
            for group in exercise_groups:
                if group['image_data']:
                    image_size = len(group['image_data'])
                    group['image_preview'] = group['image_data'][:100] + '...'  # First 100 characters
                else:
                    current_app.logger.debug(f"Group {group['id']} has no image")
            
            response_data = {
                'groups': exercise_groups,
                'count': len(exercise_groups),
                'has_images': any(group['image_data'] for group in exercise_groups)
            }
            
            current_app.logger.debug(f"Sending response with {len(exercise_groups)} groups. Has images: {response_data['has_images']}")
            
            return jsonify(response_data), 200
        else:
            current_app.logger.debug("No exercise groups found. Sending 404 response.")
            return jsonify({"message": "No exercise groups found", "groups": []}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching exercise groups: {e}")
        return jsonify({"error": "Failed to fetch exercise groups", "groups": []}), 500