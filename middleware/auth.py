from functools import wraps
from flask import request, jsonify, g
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

            session_id = auth_header.split(' ')[1]
            print("DEBUG: Extracted session_id:", session_id)

            try:
                print("DEBUG: Attempting to get session from Clerk")
                # Folosim metoda sessions.get pentru a verifica sesiunea
                session = clerk.sessions.get(
                    session_id=session_id
                )
                
                print("DEBUG: Session retrieved successfully")
                print("DEBUG: Session status:", session.status)

                # Verificăm dacă sesiunea este activă
                if session.status != "active":
                    print("DEBUG: Session is not active")
                    return jsonify({'error': 'Session is not active'}), 401

                # Setăm informațiile despre utilizator în context
                g.user_id = session.user_id
                g.session = session
                
                return f(*args, **kwargs)
            except Exception as e:
                print("DEBUG: Session retrieval failed:", str(e))
                print("DEBUG: Session ID that failed:", session_id)
                return jsonify({'error': f'Session verification failed: {str(e)}'}), 401
                
        except Exception as e:
            print("DEBUG: General authentication error:", str(e))
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401
            
    return decorated