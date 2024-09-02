from flask import Blueprint, jsonify, request, current_app
from bson import json_util, ObjectId
from datetime import datetime
import json

user_information_bp = Blueprint('user_information', __name__)

@user_information_bp.route('/', methods=['GET'])
def get_user_information():
    db_user_data = current_app.user_data
    user_info = list(db_user_data.user_information.find({}))
    print(user_info)
    return json.loads(json_util.dumps(user_info))

@user_information_bp.route('/<credentials_id>', methods=['GET'])
def get_user_info(credentials_id):
    db_user_data = current_app.user_data
    user_info = db_user_data.user_information.find_one({'credentials_id': ObjectId(credentials_id)})

    if not user_info:
        return jsonify({'error': 'User information not found'}), 404

    user_info['_id'] = str(user_info['_id'])
    user_info['credentials_id'] = str(user_info['credentials_id'])
    
    # Ensure posts and post_count fields are included
    if 'posts' not in user_info:
        user_info['posts'] = []
    if 'post_count' not in user_info:
        user_info['post_count'] = 0

    return jsonify(user_info), 200


@user_information_bp.route('/update', methods=['POST'])
def update_user_information():
    db_user_data = current_app.user_data
    data = request.get_json()

    if 'credentials_id' not in data:
        return jsonify({'error': 'Missing credentials_id'}), 400

    credentials_id = data['credentials_id']
    update_data = {
        "first_name": data.get('first_name'),
        "last_name": data.get('last_name'),
        "date_of_birth": data.get('date_of_birth'),
        "height": data.get('height'),
        "weight": data.get('weight'),
        "bio": data.get('bio')
    }

    # Remove any None values
    update_data = {k: v for k, v in update_data.items() if v is not None}

    result = db_user_data.user_information.update_one(
        {'credentials_id': ObjectId(credentials_id)},
        {'$set': update_data}
    )

    if result.matched_count == 0:
        return jsonify({'error': 'User information not found for this credentials_id'}), 404

    return jsonify({'message': 'User information updated successfully'}), 200

@user_information_bp.route('/', methods=['POST'])
def save_user_information():
    db_user_data = current_app.user_data
    data = request.get_json()

    # Validate required fields
    required_fields = ['credentials_id', 'first_name', 'last_name', 'date_of_birth']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    credentials_id = ObjectId(data['credentials_id'])

    # Check if the user already has information saved
    existing_info = db_user_data.user_information.find_one({'credentials_id': credentials_id})

    if existing_info:
        # Update existing information
        db_user_data.user_information.update_one(
            {'credentials_id': credentials_id},
            {'$set': {
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'date_of_birth': data['date_of_birth'],
                'bio': data.get('bio', ''),
                'height': data.get('height', None),
                'weight': data.get('weight', None),
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }}
        )
    else:
        # Insert new information with posts and post_count initialized
        db_user_data.user_information.insert_one({
            'credentials_id': credentials_id,
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'date_of_birth': data['date_of_birth'],
            'bio': data.get('bio', ''),
            'height': data.get('height', None),
            'weight': data.get('weight', None),
            'posts': [],  # Initialize empty posts list
            'post_count': 0,  # Initialize post count to 0
            'created_at': datetime.utcnow().isoformat() + 'Z'
        })
    
    try:
        # Update the user's profile_completed status to True in credentials
        response = db_user_data.credentials.update_one(
            {'_id': credentials_id},
            {'$set': {'profile_completed': True}}
        )

        # Retrieve updated credentials and user information
        updated_credentials = db_user_data.credentials.find_one({'_id': credentials_id})
        updated_user_info = db_user_data.user_information.find_one({'credentials_id': credentials_id})

        # Convert ObjectId to string for JSON serialization
        updated_credentials['_id'] = str(updated_credentials['_id'])
        updated_user_info['_id'] = str(updated_user_info['_id'])
        updated_user_info['credentials_id'] = str(updated_user_info['credentials_id'])

        return jsonify({
            'message': 'Profile completed successfully',
            'credentials': updated_credentials,
            'userInfo': updated_user_info
        }), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
