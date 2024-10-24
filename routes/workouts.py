from flask import Blueprint, jsonify, request, current_app
from bson import ObjectId
from datetime import datetime

workouts_bp = Blueprint('workouts', __name__)

# Route to get exercises by user_id
@workouts_bp.route('/<user_id>', methods=['GET'])
def get_exercises_by_user(user_id):
    try:
        # Access the 'saved_exercises' collection from 'user_data'
        db_saved_exercises = current_app.user_data.saved_exercises

        # Find exercises for the given user_id
        user_exercises = db_saved_exercises.find({"userId": ObjectId(user_id)})

        # Convert the cursor to a list of exercises
        exercises_list = []
        for exercise in user_exercises:
            exercises_list.append({
                "routineName": exercise.get("routineName"),
                "exercises": exercise.get("exercises"),
                "createdAt": exercise.get("createdAt"),
                "lastModified": exercise.get("lastModified")
            })

        return jsonify(exercises_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to add a new workout
@workouts_bp.route('/', methods=['POST'])
def add_workout():
    try:
        current_app.logger.debug("POST request received at /workouts")
        workout_data = request.get_json()
        current_app.logger.debug(f"Workout data received: {workout_data}")
        
        # Access the 'saved_exercises' collection from 'user_data'
        db_saved_exercises = current_app.user_data.saved_exercises
        
        workout_document = {
            "userId": ObjectId(workout_data['userId']),
            "routineName": workout_data['routineName'].strip(),
            "exercises": [
                {
                    "exercise_id": exercise['exercise_id'],
                    "exercise_name": exercise['exercise_name'],
                    "sets": [
                        {
                            "weight": float(set['weight']),
                            "reps": int(set['reps'])
                        }
                        for set in exercise['sets']
                    ],
                    "restTimer": exercise['restTimer'],
                    "order": int(exercise['order'])
                }
                for exercise in workout_data['exercises']
            ],
            "createdAt": datetime.utcnow().isoformat(),
            "lastModified": datetime.utcnow().isoformat()
        }
        
        result = db_saved_exercises.insert_one(workout_document)
        return jsonify({"message": "Workout added successfully", "id": str(result.inserted_id)}), 201
    except Exception as e:
        current_app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
