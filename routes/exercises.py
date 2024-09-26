from flask import Blueprint, jsonify, current_app, request
from Database.mysql.exercises import fetch_exercise_groups, fetch_exercises_by_group

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
    
@exercises_bp.route('/<int:group_id>', methods=['GET'])
def get_exercises_by_group(group_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = (page - 1) * limit

        exercises = fetch_exercises_by_group(group_id, limit, offset)

        current_app.logger.debug(f"Fetched {len(exercises)} exercises for group {group_id}.")

        if exercises:
            response_data = {
                'exercises': exercises,
                'count': len(exercises),
                'group_id': group_id,
                'page': page,
                'limit': limit,
                'has_more': len(exercises) == limit
            }

            current_app.logger.debug(f"Sending response with {len(exercises)} exercises for group {group_id}.")

            return jsonify(response_data), 200
        else:
            current_app.logger.debug(f"No exercises found for group {group_id}. Sending 404 response.")
            return jsonify({"message": f"No exercises found for group {group_id}", "exercises": []}), 404

    except Exception as e:
        current_app.logger.error(f"Error fetching exercises for group {group_id}: {e}")
        return jsonify({"error": f"Failed to fetch exercises for group {group_id}", "exercises": []}), 500