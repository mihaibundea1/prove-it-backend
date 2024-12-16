from flask import Blueprint, jsonify, current_app, request
from datetime import datetime
from bson import ObjectId
from scripts.question_updater import update_questions
from scripts.question_checker import check_question_changes
from middleware.auth import auth_required

questions_bp = Blueprint('questions', __name__)

def serialize_object(obj):
    """Convert MongoDB ObjectId to string and handle other types."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [serialize_object(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: serialize_object(v) for k, v in obj.items()}
    return obj

@questions_bp.route('/', methods=['GET'])
@auth_required
def get_questions():
    questions_collection = current_app.db_content.questions
    latest_questions = questions_collection.find_one(sort=[("version", -1)])
    
    if not latest_questions:
        return jsonify({"message": "No questions found"}), 404
    
    # Serialize the latest_questions object
    return jsonify(serialize_object(latest_questions)), 200

@questions_bp.route('/update_questions', methods=['POST'])
@auth_required
def api_update_questions():
    try:
        result = update_questions()  
        return jsonify({"message": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@questions_bp.route('/check_changes', methods=['GET'])
@auth_required
def check_changes():
    changes = check_question_changes()
    return jsonify(changes), 200

@questions_bp.route('/submit_answers', methods=['POST'])
@auth_required
def submit_answers():
    data = request.json
    credentials_id = data.get("credentials_id")
    answers = data.get("answers")

    # Ensure credentials_id is an ObjectId
    try:
        credentials_id = ObjectId(credentials_id)
    except Exception as e:
        return jsonify({"error": "Invalid credentials_id format"}), 400

    # Update user_information
    user_information_collection = current_app.user_data.user_information
    user_info = user_information_collection.find_one({"credentials_id": credentials_id})

    if not user_info:
        return jsonify({"error": "User information not found"}), 404

    # Include the version in the answers update
    updated_answers = {
        "version": answers.get("version"),
        "responses": answers.get("responses")
    }

    user_information_collection.update_one(
        {"credentials_id": credentials_id},
        {"$set": {"answers": updated_answers, "updated_at": datetime.utcnow()}}
    )

    # Update credentials
    credentials_collection = current_app.user_data.credentials
    credentials_collection.update_one(
        {"_id": credentials_id},
        {"$set": {"questions_completed": True}}
    )

    return jsonify({"message": "Answers saved successfully"}), 200