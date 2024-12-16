# middleware/auth.py

from functools import wraps
from flask import request, jsonify
from clerk_backend_api import Clerk

import os
from dotenv import load_dotenv


load_dotenv()

CLERK_SECRET_KEY = os.getenv('CLERK_SECRET_KEY')
if not CLERK_SECRET_KEY:
   raise ValueError("CLERK_SECRET_KEY missing from environment variables")

clerk = Clerk(CLERK_SECRET_KEY)

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # Get the token from the Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'No token provided'}), 401

            token = auth_header.split(' ')[1]
            
            # Verify the token with Clerk
            session = clerk.sessions.verify_token(token)
            
            # Add user info to flask.g for use in the route
            g.user_id = session.user_id
            g.session = session

            print(auth_header)
            
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token'}), 401
    return decorated