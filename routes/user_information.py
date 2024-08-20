from flask import Blueprint, jsonify, request, current_app
from bson import json_util, ObjectId
from datetime import datetime
import json

user_information_bp = Blueprint('user_information', __name__)

@user_information_bp.route('/', methods=['GET'])
def get_user_information():
    db_user_information = current_app.db_user_information
    user_info = list(db_user_information.user_information.find({}))
    return json.loads(json_util.dumps(user_info))

@user_information_bp.route('/<user_id>', methods=['GET'])
def get_user_info(user_id):
    db_user_information = current_app.db_user_information
    user_info = db_user_information.user_information.find_one({'user_id': ObjectId(user_id)})
    
    if not user_info:
        return jsonify({'error': 'User information not found'}), 404
    
    user_info['_id'] = str(user_info['_id'])
    user_info['user_id'] = str(user_info['user_id'])
    return jsonify(user_info), 200

@user_information_bp.route('/update', methods=['POST'])
def update_user_information():
    db_user_information = current_app.db_user_information
    data = request.get_json()

    if 'user_id' not in data:
        return jsonify({'error': 'Missing user_id'}), 400

    user_id = data['user_id']
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

    result = db_user_information.user_information.update_one(
        {'user_id': ObjectId(user_id)},
        {'$set': update_data}
    )

    if result.matched_count == 0:
        return jsonify({'error': 'User information not found for this user_id'}), 404

    return jsonify({'message': 'User information updated successfully'}), 200

@user_information_bp.route('/', methods=['POST'])
def save_user_information():
    db_user_information = current_app.db_user_information
    db_credentials = current_app.db_credentials
    data = request.get_json()

    # Validate required fields
    required_fields = ['user_id', 'first_name', 'last_name', 'date_of_birth']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    user_id = ObjectId(data['user_id'])

    # Check if the user already has information saved
    existing_info = db_user_information.user_information.find_one({'user_id': user_id})

    if existing_info:
        # Update existing information
        db_user_information.user_information.update_one(
            {'user_id': user_id},
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
        # Insert new information
        db_user_information.user_information.insert_one({
            'user_id': user_id,
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'date_of_birth': data['date_of_birth'],
            'bio': data.get('bio', ''),
            'height': data.get('height', None),
            'weight': data.get('weight', None),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        })

    try:
        # Update the user's profile_completed status to True in credentials
        db_credentials.credentials.update_one(
            {'user_id': user_id},
            {'$set': {'profile_completed': True}}
        )

        return jsonify({'message': 'Profile completed successfully'}), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
