from flask import Blueprint, jsonify, request, current_app
from bson import json_util, ObjectId
import json
from datetime import datetime
import re
import bcrypt

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    db_users = current_app.db_users
    users = list(db_users.users.find({}, {'hashed_password': 0}))  # Exclude hashed_password
    return json.loads(json_util.dumps(users))

@users_bp.route('/', methods=['POST'])
def create_user():
    db_users = current_app.db_users
    data = request.get_json()

    # Validate required fields
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    # Check if username or email already exists
    if db_users.users.find_one({'$or': [{'username': data['username']}, {'email': data['email']}]}):
        return jsonify({'error': 'Username or email already exists'}), 400

    # Process data
    user_data = {
        'username': data['username'],
        'email': data['email'],
        'hashed_password': hash_password(data['password']),  # You need to implement this function
        'bio': data.get('bio', ''),
        'profile_picture': data.get('profile_picture', ''),
        'date_of_birth': data.get('date_of_birth'),
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }

    try:
        result = db_users.users.insert_one(user_data)
        new_user = db_users.users.find_one({'_id': result.inserted_id}, {'hashed_password': 0})
        return json.loads(json_util.dumps(new_user)), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

def hash_password(password: str) -> str:
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Check if the plain password matches the hashed password
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))