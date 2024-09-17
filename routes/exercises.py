from flask import Blueprint, jsonify
from Database.mysql.exercises import fetch_exercise_groups

# Initialize the blueprint
exercises_bp = Blueprint('exercises', __name__)

@exercises_bp.route('/groups', methods=['GET'])
def get_exercise_groups():
    try:
        exercise_groups = fetch_exercise_groups()
        return exercise_groups
    except Exception as e:
        current_app.logger.error(f"Error fetching exercise groups: {e}")
        return jsonify({"error": "Failed to fetch exercise groups"}), 500
