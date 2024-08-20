from flask import Blueprint, jsonify, request, current_app
from bson import json_util, ObjectId
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
    db_credentials = current_app.db_credentials
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields for user registration
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

    # Process and insert user data
    user_data = {
        'username': data['username'],
        'email': data['email'],
        'hashed_password': hash_password(data['password']),
        'profile_completed': False,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }

    try:
        user_result = db_users.users.insert_one(user_data)
        user_id = user_result.inserted_id

        # Process and insert credentials data
        credential_data = {
            'user_id': user_id,
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'height': data.get('height'),
            'weight': data.get('weight'),
            'bio': data.get('bio', ''),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        credential_result = db_credentials.credentials.insert_one(credential_data)

        # Update the user document with the credential_id
        db_users.users.update_one({'_id': user_id}, {'$set': {'credential_id': credential_result.inserted_id}})

        # Fetch the newly created user without the hashed password
        new_user = db_users.users.find_one({'_id': user_id}, {'hashed_password': 0})

        return json.loads(json_util.dumps(new_user)), 201

    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@users_bp.route('/login', methods=['POST'])
def login_user():
    db_users = current_app.db_users
    db_credentials = current_app.db_credentials
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

    # Convert ObjectId to string for the response
    user['_id'] = str(user['_id'])

    # Convert credential_id to string if it exists
    if 'credential_id' in user:
        user['credential_id'] = str(user['credential_id'])

    # Check if the profile is completed
    if not user.get('profile_completed', False):
        return jsonify({
            'message': 'Profile incomplete, redirect to completion page',
            'user': user
        }), 200  # Use 200 OK status code for successful request

    return jsonify({'message': 'Login successful', 'user': user}), 200


# Helper functions for password hashing and verification
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
