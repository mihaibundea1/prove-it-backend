from flask import Blueprint, jsonify, request, current_app
from bson import json_util
import json

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/', methods=['GET'])
def get_posts():
    db_posts = current_app.db_posts
    posts = list(db_posts.posts.find({}))
    return json.loads(json_util.dumps(posts))

@posts_bp.route('/', methods=['POST'])
def create_post():
    db_posts = current_app.db_posts
    data = request.get_json()

    # Validate required fields
    required_fields = ['username', 'description', 'image_url']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Process data
    data['post_id'] = f"post_{ObjectId()}"  # Generate a unique post_id
    data['post_date'] = datetime.utcnow().isoformat() + 'Z'  # Set current UTC time
    data['likes'] = []  # Initialize empty likes list
    data['comments'] = []  # Initialize empty comments list

    try:
        result = db_posts.posts.insert_one(data)
        new_post = db_posts.posts.find_one({'_id': result.inserted_id})
        return json.loads(json_util.dumps(new_post)), 201
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
