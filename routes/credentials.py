from flask import Blueprint, jsonify, request, current_app
from bson import ObjectId
from bson import json_util
import json
from datetime import datetime

credentials_bp = Blueprint('credentials', __name__)

@credentials_bp.route('/', methods=['GET'])
def get_credentials():
    db_credentials = current_app.db_credentials
    credentials = list(db_credentials.credentials.find({})) 
    return json.loads(json_util.dumps(credentials))

@credentials_bp.route('/<user_id>', methods=['GET'])
def get_user_credentials(user_id):
    db_credentials = current_app.db_credentials
    credentials = db_credentials.credentials.find_one({'user_id': ObjectId(user_id)})
    
    if not credentials:
        return jsonify({'error': 'Credentials not found'}), 404
    
    credentials['_id'] = str(credentials['_id'])
    credentials['user_id'] = str(credentials['user_id'])
    return jsonify(credentials), 200

@credentials_bp.route('/update', methods=['POST'])
def update_user_credentials():
    db_credentials = current_app.db_credentials
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
        "description": data.get('description')
    }

    # Remove any None values
    update_data = {k: v for k, v in update_data.items() if v is not None}

    result = db_credentials.credentials.update_one(
        {'user_id': ObjectId(user_id)},
        {'$set': update_data}
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Credentials not found for this user_id'}), 404

    return jsonify({'message': 'Credentials updated successfully'}), 200

@credentials_bp.route('/', methods=['POST'])
def save_user_credentials():
    db_credentials = current_app.db_credentials
    db_users = current_app.db_users
    data = request.get_json()

    # Validate required fields
    required_fields = ['user_id', 'first_name', 'last_name', 'date_of_birth']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    user_id = ObjectId(data['user_id'])

    # Check if the user already has credentials saved
    existing_credentials = db_credentials.credentials.find_one({'user_id': user_id})

    if existing_credentials:
        # Update existing credentials
        db_credentials.credentials.update_one(
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
        # Insert new credentials
        db_credentials.credentials.insert_one({
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
        # Update the user's profile_completed status to True
        db_users.users.update_one(
            {'_id': user_id},
            {'$set': {'profile_completed': True}}
        )

        return jsonify({'message': 'Profile completed successfully'}), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
