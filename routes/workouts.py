from flask import Blueprint, jsonify, request, current_app
from bson import ObjectId
from datetime import datetime

workouts_bp = Blueprint('workouts', __name__)

@workouts_bp.route('/<user_id>', methods=['GET'])
def get_exercises_by_user(user_id):
    try:
        # Access the saved_exercises collection
        exercises_collection = current_app.user_data.saved_exercises

        # Find user's workout document
        user_workouts = exercises_collection.find_one({"user_id": ObjectId(user_id)})
        
        if not user_workouts or "workouts" not in user_workouts:
            return jsonify([]), 200

        return jsonify(user_workouts["workouts"]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@workouts_bp.route('/', methods=['POST'])
def add_workout():
    try:
        current_app.logger.debug("POST request received at /workouts")
        workout_data = request.get_json()
        current_app.logger.debug(f"Workout data received: {workout_data}")
        
        # Access the saved_exercises collection
        exercises_collection = current_app.user_data.saved_exercises
        
        new_workout = {
            "workout_id": str(ObjectId()),
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
        
        # Update or create the user's workout document
        result = exercises_collection.update_one(
            {"user_id": ObjectId(workout_data['userId'])},
            {
                "$push": {"workouts": new_workout},
                "$setOnInsert": {
                    "user_id": ObjectId(workout_data['userId']),
                    "created_at": datetime.utcnow().isoformat()
                },
                "$set": {
                    "updated_at": datetime.utcnow().isoformat()
                }
            },
            upsert=True
        )
        
        return jsonify({
            "message": "Workout added successfully",
            "workout_id": new_workout["workout_id"]
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@workouts_bp.route('/<user_id>/<workout_id>', methods=['PUT'])
def update_workout(user_id, workout_id):
    try:
        workout_data = request.get_json()
        exercises_collection = current_app.user_data.saved_exercises
        
        updated_workout = {
            "workout_id": workout_id,
            "routineName": workout_data['routineName'].strip(),
            "exercises": workout_data['exercises'],
            "lastModified": datetime.utcnow().isoformat()
        }
        
        result = exercises_collection.update_one(
            {
                "user_id": ObjectId(user_id),
                "workouts.workout_id": workout_id
            },
            {
                "$set": {
                    "workouts.$": updated_workout,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Workout not found"}), 404
            
        return jsonify({"message": "Workout updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@workouts_bp.route('/<user_id>/<workout_id>', methods=['DELETE'])
def delete_workout(user_id, workout_id):
    try:
        exercises_collection = current_app.user_data.saved_exercises
        
        result = exercises_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$pull": {
                    "workouts": {"workout_id": workout_id}
                },
                "$set": {
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Workout not found"}), 404
            
        return jsonify({"message": "Workout deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500