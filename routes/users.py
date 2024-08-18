from flask import Blueprint, jsonify, request, current_app
from bson import json_util
from datetime import datetime
import re
import bcrypt
import json

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    db_users = current_app.db_users
    users = list(db_users.users.find({}, {'hashed_password': 0}))  # Exclude hashed_password
    return json.loads(json_util.dumps(users))

@users_bp.route('/register', methods=['POST'])
def register_user():
    db_users = current_app.db_users
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    if db_users.users.find_one({'$or': [{'username': data['username']}, {'email': data['email']}]}):
        return jsonify({'error': 'Username or email already exists'}), 400

    user_data = {
        'username': data['username'],
        'email': data['email'],
        'hashed_password': hash_password(data['password']),
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }

    try:
        result = db_users.users.insert_one(user_data)
        new_user = db_users.users.find_one({'_id': result.inserted_id}, {'hashed_password': 0})
        return json.loads(json_util.dumps(new_user)), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@users_bp.route('/login', methods=['POST'])
def login_user():
    db_users = current_app.db_users
    data = request.get_json()

    # Validate required fields
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Find user by email
    user = db_users.users.find_one({'email': data['email']})
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    # Verify password
    if not verify_password(data['password'], user['hashed_password']):
        return jsonify({'error': 'Invalid password'}), 401

    # Remove hashed_password from the user data
    user.pop('hashed_password', None)

    # Convert ObjectId to string
    user['_id'] = str(user['_id'])

    return jsonify({'message': 'Login successful', 'user': user}), 200

def hash_password(password: str) -> str:
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Check if the plain password matches the hashed password
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
