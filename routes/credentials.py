from flask import Blueprint, jsonify, request, current_app
from bson import json_util, ObjectId
from datetime import datetime
import re
import bcrypt
import json

credentials_bp = Blueprint('credentials', __name__)

@credentials_bp.route('/', methods=['GET'])
def get_credentials():
    db_user_data = current_app.user_data
    credentials = list(db_user_data.credentials.find({}, {'hashed_password': 0}))  # Exclude hashed_password
    return json.loads(json_util.dumps(credentials))

@credentials_bp.route('/register', methods=['POST'])
def register_user():
    db_user_data = current_app.user_data
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
    if db_user_data.credentials.find_one({'$or': [{'username': data['username']}, {'email': data['email']}]}):
        return jsonify({'error': 'Username or email already exists'}), 400

    # Process and insert credential data
    credential_data = {
        'username': data['username'],
        'email': data['email'],
        'hashed_password': hash_password(data['password']),
        'profile_completed': False,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'last_login': None
    }
    try:
        credential_result = db_user_data.credentials.insert_one(credential_data)
        credentials_id = credential_result.inserted_id

        # Process and insert user information data with posts and post_count initialized
        user_info_data = {
            'credentials_id': credentials_id,
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'height': data.get('height'),
            'weight': data.get('weight'),
            'bio': data.get('bio', ''),
            'posts': [],  # Initialize empty posts list
            'post_count': 0,  # Initialize post count to 0
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        db_user_data.user_information.insert_one(user_info_data)

        # Fetch the newly created credentials without the hashed password
        new_credentials = db_user_data.credentials.find_one({'_id': credentials_id}, {'hashed_password': 0})

        return json.loads(json_util.dumps(new_credentials)), 201

    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@credentials_bp.route('/login', methods=['POST'])
def login_user():
    db_user_data = current_app.user_data
    data = request.get_json()

    # Validate required fields
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Find user by email
    credentials = db_user_data.credentials.find_one({'email': data['email']})

    if credentials is None:
        return jsonify({'error': 'User not found'}), 404 

    # Verify password
    if not verify_password(data['password'], credentials['hashed_password']):
        return jsonify({'error': 'Invalid password'}), 401

    # Remove hashed_password from the credentials data
    credentials.pop('hashed_password', None)

    # Update last login
    db_user_data.credentials.update_one(
        {'_id': credentials['_id']},
        {'$set': {'last_login': datetime.utcnow().isoformat() + 'Z'}}
    )

    # Convert ObjectId to string for the response
    credentials['_id'] = str(credentials['_id'])

    # Fetch user information based on credentials ID
    user_info = db_user_data.user_information.find_one({'credentials_id': ObjectId(credentials['_id'])})

    if user_info:
        # Convert ObjectId fields to strings
        user_info['_id'] = str(user_info['_id'])
        user_info['credentials_id'] = str(user_info['credentials_id'])

    # Check if the profile is completed
    if not credentials.get('profile_completed', False):
        return jsonify({
            'message': 'Profile incomplete, redirect to completion page',
            'credentials': credentials,
            'userInfo': user_info
        }), 200  # Use 200 OK status code for successful request
    
    return jsonify({'message': 'Login successful', 'credentials': credentials, 'userInfo': user_info}), 200

# Helper functions for password hashing and verification
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
