from flask import Blueprint, jsonify
from Database.mysql.exercises import fetch_exercises

# Initialize the blueprint
exercises_bp = Blueprint('exercises', __name__)

@exercises_bp.route('/', methods=['GET'])
def get_exercises():
    print("aici")
    try:
        result = fetch_exercises()
        print(result)
        return result
    except Exception as e:
        return jsonify({"error": str(e)}), 500
