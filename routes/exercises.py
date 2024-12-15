from flask import Blueprint, jsonify, current_app, request
from Database.mysql.exercises import fetch_all_exercises, fetch_exercise_groups, fetch_exercises_by_group, fetch_exercise_details

exercises_bp = Blueprint('exercises', __name__)

@exercises_bp.route('/all', methods=['GET'])
def get_all_exercises():
    try:
        cache_manager = current_app.exercises_cache
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 1000, type=int)
        
        # Get exercises from cache
        exercises = cache_manager.get_exercises()
        thumbnails_processing = False
        
        # If cache is empty, initialize it
        if not exercises:
            current_app.logger.info("Cache miss - initializing cache")
            num_exercises = cache_manager.initialize_cache()
            if num_exercises > 0:
                exercises = cache_manager.get_exercises()
                thumbnails_processing = True  # New cache always needs processing
            else:
                current_app.logger.error("Failed to initialize cache")
                return jsonify({'error': 'Failed to fetch exercises'}), 500
        else:
            # Check for missing thumbnails in existing cache
            thumbnails_processing = cache_manager.check_missing_thumbnails(exercises)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        return jsonify({
            'exercises': exercises[start_idx:end_idx],
            'page': page,
            'limit': limit,
            'total': len(exercises),
            'thumbnails_processing': thumbnails_processing
        })
        
    except Exception as e:
        current_app.logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    
@exercises_bp.route('/groups', methods=['GET'])
def get_exercise_groups():
    try:
        exercise_groups = fetch_exercise_groups()
        
        current_app.logger.debug(f"Fetched {len(exercise_groups)} exercise groups.")
        
        if exercise_groups:
            # Add debug information
            for group in exercise_groups:
                image_url = group.get('image_url')
                current_app.logger.debug(
                    f"Group {group['id']} image URL: " + 
                    (image_url[:100] + '...' if image_url else 'None')
                )
            
            response_data = {
                'groups': exercise_groups,
                'count': len(exercise_groups),
                'has_images': any(group.get('image_url') for group in exercise_groups)
            }
            
            current_app.logger.debug(
                f"Sending response with {len(exercise_groups)} groups. " +
                f"Has images: {response_data['has_images']}"
            )
            
            return jsonify(response_data), 200
        else:
            current_app.logger.debug("No exercise groups found. Sending 404 response.")
            return jsonify({
                "message": "No exercise groups found", 
                "groups": []
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error fetching exercise groups: {e}")
        return jsonify({
            "error": "Failed to fetch exercise groups", 
            "groups": []
        }), 500
    
@exercises_bp.route('/<int:group_id>', methods=['GET'])
def get_exercises_by_group(group_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = (page - 1) * limit

        exercises = fetch_exercises_by_group(group_id, limit, offset)
        
        current_app.logger.debug(f"Fetched {len(exercises)} exercises for group {group_id}.")

        if exercises:
            # Add debug information for images
            for exercise in exercises:
                image_url = exercise.get('image_url')
                current_app.logger.debug(
                    f"Exercise {exercise['exercise_id']} image URL: " +
                    (image_url[:100] + '...' if image_url else 'None')
                )
            
            response_data = {
                'exercises': exercises,
                'count': len(exercises),
                'group_id': group_id,
                'page': page,
                'limit': limit,
                'has_more': len(exercises) == limit,
                'has_images': any(exercise.get('image_url') for exercise in exercises)
            }

            current_app.logger.debug(
                f"Sending response with {len(exercises)} exercises for group {group_id}. " +
                f"Page: {page}, Limit: {limit}"
            )

            return jsonify(response_data), 200
        else:
            current_app.logger.debug(
                f"No exercises found for group {group_id}. Sending 404 response."
            )
            return jsonify({
                "message": f"No exercises found for group {group_id}", 
                "exercises": []
            }), 404

    except Exception as e:
        current_app.logger.error(f"Error fetching exercises for group {group_id}: {e}")
        return jsonify({
            "error": f"Failed to fetch exercises for group {group_id}", 
            "exercises": []
        }), 500
    
@exercises_bp.route('/details/<string:exercise_id>', methods=['GET'])
def get_exercise_details(exercise_id):
    try:
        current_app.logger.debug(f"Fetching details for exercise: {exercise_id}")
        exercise_details = fetch_exercise_details(exercise_id)
        
        if exercise_details:
            # Add debug information for images
            if exercise_details.get('images'):
                for i, image_url in enumerate(exercise_details['images']):
                    current_app.logger.debug(
                        f"Exercise {exercise_id} image {i} URL: " +
                        (image_url[:100] + '...' if image_url else 'None')
                    )
            
            response_data = {
                "exercise": exercise_details,
                "has_images": bool(exercise_details.get('images')),
                "images_count": len(exercise_details.get('images', []))
            }
            
            current_app.logger.debug(
                f"Sending response for exercise {exercise_id} with " +
                f"{response_data['images_count']} images"
            )
            
            return jsonify(response_data), 200
        else:
            current_app.logger.debug(f"Exercise {exercise_id} not found")
            return jsonify({
                "error": "Exercise not found",
                "exercise_id": exercise_id
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error fetching details for exercise {exercise_id}: {e}")
        return jsonify({
            "error": f"Failed to fetch exercise details",
            "exercise_id": exercise_id,
            "message": str(e)
        }), 500

# Adăugăm și endpoint-uri pentru managementul cache-ului
@exercises_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    try:
        exercise_id = request.args.get('exercise_id')
        group_id = request.args.get('group_id')
        
        from Database.mysql.exercises import clear_exercise_cache
        success = clear_exercise_cache(exercise_id, group_id)
        
        if success:
            message = (
                f"Cache cleared successfully for " +
                (f"exercise {exercise_id}" if exercise_id else "") +
                (f"group {group_id}" if group_id else "") +
                ("all exercises" if not exercise_id and not group_id else "")
            )
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": "Failed to clear cache"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": "Failed to clear cache", "message": str(e)}), 500