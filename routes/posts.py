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
    db_posts = current_app.db_posts
    posts = list(db_posts.posts.find({}).sort('post_date', -1))


    for post in posts:
        if 'image_url' in post:
            presigned_url = s3_helpers.generate_presigned_url(post['image_url'])
            if presigned_url:
                post['image_url'] = presigned_url
            else:
                post['image_url'] = None  # or handle this case as appropriate

    return json.loads(json_util.dumps(posts))

@posts_bp.route('/', methods=['POST'])
def create_post():
    db_posts = current_app.db_posts
    s3_manager = current_app.s3_manager

    # Extract form data
    username = request.form.get('username')
    description = request.form.get('description')
    image = request.files.get('image')

    # Validate required fields
    if not username or not description or not image:
        return jsonify({'error': 'Missing required fields'}), 400

    # Secure the filename and ensure it has an extension
    filename = secure_filename(image.filename)
    if not filename:
        return jsonify({'error': 'Invalid file name'}), 400

    # Ensure the file extension is included in the object key
    file_extension = os.path.splitext(filename)[1]  # Get the file extension
    if not file_extension:
        return jsonify({'error': 'File must have an extension'}), 400

    object_key = f"posts/{filename}"  # Define the S3 object key

    try:
        # Upload the image to S3
        s3_manager.upload_fileobj(image, 'proveit-posts-images', object_key)  # Replace with your bucket name

        # Generate the image URL
        image_url = f"https://eu-north-1.console.aws.amazon.com/s3/object/proveit-posts-images?region=eu-north-1&bucketType=general&prefix={object_key}"  # Adjust URL format if necessary

        # Create the post data
        post_data = {
            'username': username,
            'description': description,
            'image_url': image_url,  # Save the S3 URL
            'post_id': f"post_{ObjectId()}",  # Generate a unique post_id
            'post_date': datetime.utcnow().isoformat() + 'Z',  # Set current UTC time
            'likes': [],  # Initialize empty likes list
            'comments': []  # Initialize empty comments list
        }

        # Insert the post data into the database
        result = db_posts.posts.insert_one(post_data)
        new_post = db_posts.posts.find_one({'_id': result.inserted_id})
        return json.loads(json_util.dumps(new_post)), 201

    except Exception as e:
        # Handle errors during S3 upload or database insertion
        return jsonify({'error': f'Error uploading file or saving post: {str(e)}'}), 500