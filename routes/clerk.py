from flask import Blueprint, request, jsonify
from clerk_backend_api import Clerk
from functools import wraps
import os
import httpx

clerk_routes = Blueprint('clerk', __name__)
clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))

def handle_clerk_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': str(e),
                'message': getattr(e, 'message', 'An error occurred')
            }), 400
    return wrapper

@clerk_routes.route('/sign-in', methods=['POST'])
@handle_clerk_error
def sign_in():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    try:
        # Creează sesiunea de sign in
        sign_in_attempt = clerk.sign_ins.create(
            identifier=email,
            password=password
        )
        
        # Verifică dacă sign in-ul a fost completat cu succes
        if sign_in_attempt.status == 'complete':
            return jsonify({
                'success': True,
                'sessionId': sign_in_attempt.created_session_id,
                'token': sign_in_attempt.token
            })
        
        return jsonify({
            'success': False,
            'message': 'Sign in incomplete'
        }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@clerk_routes.route('/sign-up', methods=['POST'])
@handle_clerk_error
def sign_up():
    data = request.json
    
    try:
        # Creează userul în Clerk
        user = clerk.users.create(
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            username=data.get('username'),
            email_address=[{"email_address": data.get('email')}],
            password=data.get('password')
        )
        
        # Pregătește verificarea emailului
        verification = clerk.email_addresses.create_email_verification(
            email_address_id=user.email_addresses[0].id
        )
        
        return jsonify({
            'success': True,
            'userId': user.id,
            'verificationId': verification.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@clerk_routes.route('/verify-email', methods=['POST'])
@handle_clerk_error
def verify_email():
    data = request.json
    code = data.get('code')
    user_id = data.get('userId')
    
    try:
        # Verifică codul
        verification = clerk.email_addresses.verify_email_verification(
            email_verification_id=user_id,
            code=code
        )
        
        if verification.verification_status == 'verified':
            # Creează informațiile utilizatorului în baza ta de date
            user_info = {
                'clerkId': user_id,
                'date_of_birth': None,
                'height': 0,
                'weight': 0,
                'bio': "",
                'posts': [],
                'post_count': 0,
                'followers': [],
                'followers_count': 0,
                'following': [],
                'following_count': 0,
                'created_at': None,
                'updated_at': None,
                'questions_completed': False,
                'profile_completed': False,
                'answers': {
                    'version': 1,
                    'responses': {}
                }
            }
            
            # Aici ar trebui să adaugi logica pentru a salva user_info în baza ta de date
            
            return jsonify({
                'success': True,
                'message': 'Email verified successfully'
            })
            
        return jsonify({
            'success': False,
            'message': 'Email verification failed'
        }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

# Rută pentru retrimiterea codului de verificare
@clerk_routes.route('/resend-verification', methods=['POST'])
@handle_clerk_error
def resend_verification():
    data = request.json
    user_id = data.get('userId')
    
    try:
        # Retrimiți codul de verificare
        verification = clerk.email_addresses.create_email_verification(
            email_address_id=user_id
        )
        
        return jsonify({
            'success': True,
            'verificationId': verification.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400