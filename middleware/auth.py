from functools import wraps
from flask import request, jsonify, g
import jwt
import requests  # To fetch Clerk's JWKs
import os
from dotenv import load_dotenv

load_dotenv()

# Replace CLERK_SECRET_KEY with CLERK_JWKS_URL
CLERK_JWKS_URL = os.getenv('CLERK_JWKS_URL')
if not CLERK_JWKS_URL:
    raise ValueError("CLERK_JWKS_URL missing from environment variables")

def get_public_key(token):
    """Fetches and returns the public key for a given JWT."""
    response = requests.get(CLERK_JWKS_URL)
    jwks = response.json()

    # Extract `kid` from token header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get('kid')

    if not kid:
        raise ValueError("Token is missing 'kid' in header")

    # Find the matching key in the JWKs
    for key in jwks['keys']:
        if key['kid'] == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)

    raise ValueError("Public key not found for the given token")

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            print("=== Auth Debug ===")
            print("Full headers received:", dict(request.headers))
            print("Auth header received:", auth_header)

            if not auth_header:
                print("DEBUG: No Authorization header found")
                return jsonify({'error': 'No Authorization header provided'}), 401

            if not auth_header.startswith('Bearer '):
                print("DEBUG: Invalid Authorization format:", auth_header)
                return jsonify({'error': 'Invalid Authorization header format'}), 401

            token = auth_header.split(' ')[1]
            print("DEBUG: Extracted token:", token)

            try:
                print("DEBUG: Decoding JWT")
                # Fetch and use the public key for verification
                public_key = get_public_key(token)
                payload = jwt.decode(token, public_key, algorithms=['RS256']
                                     # is a good idea to add audience
                                     # to the token, it is the url of the backend
                                     # it is being configured in clerk
                                     # , issuer='your-backend-issuer'
                                     # which is gonn a be like api.fitversehub.com....
                                     # or whatever
                                     # , audience='your-backend-audience'
                )
                print("DEBUG: Decoded payload:", payload)

                # Add user information to Flask's global context (g)
                g.user_id = payload.get('sub')  # Clerk uses `sub` for user ID
                g.payload = payload

                return f(*args, **kwargs)

            except jwt.ExpiredSignatureError:
                print("DEBUG: Token expired")
                return jsonify({'error': 'Token expired'}), 401
            except jwt.InvalidTokenError as e:
                print("DEBUG: Invalid token:", str(e))
                return jsonify({'error': f'Invalid token: {str(e)}'}), 401

        except Exception as e:
            print("DEBUG: General authentication error:", str(e))
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401

    return decorated
