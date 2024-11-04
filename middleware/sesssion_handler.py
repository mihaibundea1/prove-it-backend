from functools import wraps
from flask import request, jsonify
from typing import Optional, Dict, Any
import jwt
from datetime import datetime
import requests
from core.redis_manager import RedisManager

class ClerkSessionHandler:
    _instance = None
    
    def __new__(cls) -> 'ClerkSessionHandler':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_handler()
        return cls._instance
    
    def _initialize_handler(self) -> None:
        self.redis = RedisManager()
        self.clerk_public_key = "your_clerk_public_key"  # Load from env
        self.clerk_jwt_template = "https://clerk.your-domain.com/.well-known/jwks.json"
        
    def verify_session(self, f):
        """Decorator pentru verificarea sesiunii Clerk"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'No token provided'}), 401
            
            token = auth_header.split(' ')[1]
            user_data = self._validate_token(token)
            
            if not user_data:
                return jsonify({'error': 'Invalid or expired token'}), 401
                
            # Atașăm datele userului la request pentru a fi disponibile în route
            request.user = user_data
            return f(*args, **kwargs)
            
        return decorated_function
    
    def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validează JWT-ul de la Clerk și returnează datele userului"""
        cache_key = f"clerk_session:{token}"
        
        # Verifică mai întâi în cache
        cached_data = self.redis.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Decodifică și verifică JWT-ul
            decoded = jwt.decode(
                token,
                self.clerk_public_key,
                algorithms=["RS256"],
                audience="your-audience",  # Configure from env
                options={"verify_aud": True}
            )
            
            user_data = {
                'user_id': decoded['sub'],
                'email': decoded.get('email'),
                'session_id': decoded.get('sid'),
                'device_id': request.headers.get('X-Device-Id'),
                'platform': request.headers.get('X-Platform', 'web'),
                'last_active': datetime.utcnow().isoformat()
            }
            
            # Cache user data with short TTL
            self.redis.set(cache_key, user_data, expires_in=300)  # 5 minute cache
            
            return user_data
            
        except jwt.InvalidTokenError as e:
            print(f"Token validation error: {e}")
            return None
            
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Helper pentru a obține datele userului curent"""
        if hasattr(request, 'user'):
            return request.user
        return None