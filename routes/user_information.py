from flask import Blueprint, jsonify, request, current_app, session
from bson import json_util, ObjectId
from datetime import datetime
import json
from middleware.auth import auth_required

user_information_bp = Blueprint('user_information', __name__)

@user_information_bp.route('/register', methods=['POST'])
@auth_required
def register_user_information():
    db_user_data = current_app.user_data
    data = request.get_json()

    # Validăm că avem clerkId
    if 'clerkId' not in data:
        return jsonify({'error': 'Missing clerkId'}), 400

    clerk_id = data['clerkId']

    # Verificăm dacă utilizatorul există deja
    existing_info = db_user_data.user_information.find_one({'clerkId': clerk_id})

    if existing_info:
        return jsonify({'error': 'User already exists'}), 409

    # Creăm documentul nou
    new_user = {
        'clerkId': clerk_id,
        'date_of_birth': data.get('date_of_birth'),
        'height': data.get('height', 0),
        'weight': data.get('weight', 0),
        'bio': data.get('bio', ''),
        'posts': [],
        'post_count': 0,
        'followers': [],
        'followers_count': 0,
        'following': [],
        'following_count': 0,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'questions_completed': False,
        'profile_completed': False,
        'answers': {
            'version': 1,
            'responses': {}
        }
    }

    try:
        result = db_user_data.user_information.insert_one(new_user)
        new_user['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': new_user
        }), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@user_information_bp.route('/', methods=['GET'])
@auth_required
def get_user_information():
    db_user_data = current_app.user_data
    user_info = list(db_user_data.user_information.find({}))
    print(user_info)
    return json.loads(json_util.dumps(user_info))

@user_information_bp.route('/<credentials_id>', methods=['GET'])
@auth_required
def get_user_info(credentials_id):
    db_user_data = current_app.user_data
    user_info = db_user_data.user_information.find_one({'credentials_id': ObjectId(credentials_id)})

    if not user_info:
        return jsonify({'error': 'User information not found'}), 404

    # Convert ObjectId fields to strings
    user_info['_id'] = str(user_info['_id'])
    user_info['credentials_id'] = str(user_info['credentials_id'])

    # Ensure posts, followers, and following fields are included
    if 'posts' not in user_info:
        user_info['posts'] = []
    if 'post_count' not in user_info:
        user_info['post_count'] = 0
    if 'followers' not in user_info:
        user_info['followers'] = []
    if 'following' not in user_info:
        user_info['following'] = []
    if 'followers_count' not in user_info:
        user_info['followers_count'] = 0
    if 'following_count' not in user_info:
        user_info['following_count'] = 0

    # Convert followers and following lists to strings
    user_info['followers'] = [str(follower) for follower in user_info.get('followers', [])]
    user_info['following'] = [str(following) for following in user_info.get('following', [])]
    
    if 'answers' not in user_info:
        user_info['answers'] = {}

    return jsonify(user_info), 200



@user_information_bp.route('/update', methods=['POST'])
@auth_required
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
@auth_required
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
        # Insert new information with posts, followers, and following initialized
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
            'followers': [],  # Initialize empty followers list
            'following': [],  # Initialize empty following list
            'followers_count': 0,  # Initialize followers count to 0
            'following_count': 0,  # Initialize following count to 0
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
    
from bson import ObjectId  # Make sure you import ObjectId

@user_information_bp.route('/follow/<id>', methods=['POST'])
@auth_required
def follow_user(id):
    db_user_data = current_app.user_data

    # Use the credentials_id passed in the request body
    data = request.get_json()
    if not data or 'credentials_id' not in data:
        return jsonify({'error': 'Missing credentials_id'}), 400
    
    follower_id = ObjectId(data['credentials_id'])  # Convert to ObjectId
    following_id = ObjectId(id)  # Convert the followee ID to ObjectId

    # Update following/followers list and counts
    db_user_data.user_information.update_one(
        {'credentials_id': follower_id},
        {
            '$addToSet': {'following': str(following_id)},  # Store as string
            '$inc': {'following_count': 1}  # Increment following count
        }
    )
    db_user_data.user_information.update_one(
        {'credentials_id': following_id},
        {
            '$addToSet': {'followers': str(follower_id)},  # Store as string
            '$inc': {'followers_count': 1}  # Increment followers count
        }
    )

    return jsonify({'message': 'Followed user successfully'}), 200


@user_information_bp.route('/unfollow/<followee_id>', methods=['POST'])
@auth_required
def unfollow_user(followee_id):
    db_user_data = current_app.user_data

    # Use the credentials_id passed in the request body
    data = request.get_json()
    if not data or 'credentials_id' not in data:
        return jsonify({'error': 'Missing credentials_id'}), 400
    
    follower_id = ObjectId(data['credentials_id'])  # Convert to ObjectId

    # Remove followee from follower's following list and update counts
    db_user_data.user_information.update_one(
        {'credentials_id': follower_id},
        {
            '$pull': {'following': str(followee_id)},  # Store as string
            '$inc': {'following_count': -1}  # Decrement following count
        }
    )

    # Remove follower from followee's followers list and update counts
    db_user_data.user_information.update_one(
        {'credentials_id': ObjectId(followee_id)},  # Convert to ObjectId
        {
            '$pull': {'followers': str(follower_id)},  # Store as string
            '$inc': {'followers_count': -1}  # Decrement followers count
        }
    )

    return jsonify({'message': 'Unfollow successful'}), 200


@user_information_bp.route('/is_following/<target_user_id>', methods=['GET'])
@auth_required
def is_following(target_user_id):
    db_user_data = current_app.user_data

    # Check if credentials_id is provided in query parameters
    if 'credentials_id' not in request.args:
        return jsonify({'error': 'User not logged in'}), 401

    follower_id = ObjectId(request.args['credentials_id'])  # Convert to ObjectId
    target_user_id = ObjectId(target_user_id)  # Convert to ObjectId

    # Check if follower_id is in the following list of the logged-in user
    user_info = db_user_data.user_information.find_one(
        {'credentials_id': follower_id, 'following': str(target_user_id)}  # Store as string
    )

    is_following = user_info is not None
    return jsonify({'is_following': is_following}), 200
