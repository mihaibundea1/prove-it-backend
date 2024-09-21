from flask import Blueprint, jsonify, request, current_app
from bson import json_util
import json
from werkzeug.utils import secure_filename
from utils import s3_helpers
from datetime import datetime
from bson.objectid import ObjectId
import os

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/', methods=['GET'])
def get_posts():
    db_content = current_app.db_content

    # Get the credentials_id from the query parameters
    credentials_id = request.args.get('credentials_id')

    # If credentials_id is provided, filter posts by this user
    query = {}
    if credentials_id:
        query['credentials_id'] = credentials_id

    # Fetch posts from the database based on the query
    posts = list(db_content.posts.find(query).sort('post_date', -1))

    # Generate presigned URL for the post images
    for post in posts:
        if 'image_url' in post:
            presigned_url = s3_helpers.generate_presigned_url(post['image_url'])
            if presigned_url:
                post['image_url'] = presigned_url
            else:
                post['image_url'] = None  # handle this case as appropriate

    return json.loads(json_util.dumps(posts))


@posts_bp.route('/', methods=['POST'])
def create_post():
    db_content = current_app.db_content
    db_user_data = current_app.user_data  # Access user data
    s3_manager = current_app.s3_manager

    credentials_id = request.form.get('credentials_id')  # Get the user's credentials_id
    username = request.form.get('username')
    description = request.form.get('description')
    image = request.files.get('image')

    if not credentials_id or not username or not description or not image:
        return jsonify({'error': 'Missing required fields'}), 400

    filename = secure_filename(image.filename)
    if not filename:
        return jsonify({'error': 'Invalid file name'}), 400

    file_extension = os.path.splitext(filename)[1]
    if not file_extension:
        return jsonify({'error': 'File must have an extension'}), 400

    object_key = f"posts/{filename}"

    try:
        s3_manager.upload_fileobj(image, 'proveit-posts-images', object_key)  # Replace with your bucket name
        image_url = f"https://eu-north-1.console.aws.amazon.com/s3/object/proveit-posts-images?region=eu-north-1&bucketType=general&prefix={object_key}"

        post_id = f"post_{ObjectId()}"
        post_data = {
            'post_id': post_id,
            'credentials_id': credentials_id,
            'username': username,
            'description': description,
            'image_url': image_url,
            'post_date': datetime.utcnow().isoformat() + 'Z',
            'like_count': 0,
            'comment_count': 0,
            'likes': [],
            'comments': []
        }

        result = db_content.posts.insert_one(post_data)

        db_user_data.user_information.update_one(
            {'credentials_id': ObjectId(credentials_id)},
            {
                '$push': {'posts': post_id},
                '$inc': {'post_count': 1}
            }
        )

        new_post = db_content.posts.find_one({'_id': result.inserted_id})
        return json.loads(json_util.dumps(new_post)), 201

    except Exception as e:
        return jsonify({'error': f'Error uploading file or saving post: {str(e)}'}), 500

@posts_bp.route('/like/<post_id>', methods=['POST'])
def like_post(post_id):
    db_content = current_app.db_content
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    like_id = str(ObjectId())
    like_date = datetime.utcnow().isoformat() + 'Z'

    like = {
        'like_id': like_id,
        'username': username,
        'date': like_date
    }

    result = db_content.posts.update_one(
        {'post_id': post_id},
        {
            '$addToSet': {'likes': like},
            '$inc': {'like_count': 1}
        }
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({'message': 'Post liked successfully', 'like_id': like_id}), 200

@posts_bp.route('/unlike/<post_id>/<like_id>', methods=['DELETE'])
def unlike_post(post_id, like_id):
    db_content = current_app.db_content

    # Remove the like from the post
    result = db_content.posts.update_one(
        {'post_id': post_id},
        {
            '$pull': {'likes': {'like_id': like_id}},
            '$inc': {'like_count': -1}
        }
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({'message': 'Post unliked successfully'}), 200


@posts_bp.route('/comment/<post_id>', methods=['POST'])
def comment_post(post_id):
    db_content = current_app.db_content
    data = request.get_json()
    username = data.get('username')
    comment_text = data.get('comment')

    if not username or not comment_text:
        return jsonify({'error': 'Username and comment are required'}), 400

    comment_id = str(ObjectId())
    comment_date = datetime.utcnow().isoformat() + 'Z'

    comment = {
        'comment_id': comment_id,
        'username': username,
        'comment': comment_text,
        'comment_date': comment_date
    }

    result = db_content.posts.update_one(
        {'post_id': post_id},
        {
            '$addToSet': {'comments': comment},
            '$inc': {'comment_count': 1}
        }
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({'message': 'Comment added successfully', 'comment_id': comment_id}), 200

@posts_bp.route('/delete_comment/<post_id>/<comment_id>', methods=['DELETE'])
def delete_comment(post_id, comment_id):
    db_content = current_app.db_content

    result = db_content.posts.update_one(
        {'post_id': post_id},
        {
            '$pull': {'comments': {'comment_id': comment_id}},
            '$inc': {'comment_count': -1}
        }
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({'message': 'Comment deleted successfully'}), 200
