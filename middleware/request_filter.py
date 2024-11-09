# middleware/request_filter.py
from flask import request, jsonify
from functools import wraps
from typing import List, Dict, Optional, Callable
import re
from datetime import datetime
from core.redis_manager import RedisManager

class RequestFilter:
    _instance = None
    
    def __new__(cls) -> 'RequestFilter':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_filter()
        return cls._instance
        
    def _initialize_filter(self) -> None:
        self.redis = RedisManager()
        self.blocked_ips: List[str] = []
        self.required_headers = ['X-Api-Key', 'X-Client-Version']
        self.allowed_paths = [
            r'^/api/v1/.*',
            r'^/health$',
            r'^/metrics$'
        ]
        
    def validate_request(self) -> Callable:
        """Main request validation decorator"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Check if IP is blocked
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if self._is_ip_blocked(client_ip):
                    return self._error_response("IP address is blocked", 403)
                
                # Validate path
                if not self._is_valid_path(request.path):
                    return self._error_response("Invalid path", 404)
                
                # Check required headers
                missing_headers = self._check_required_headers()
                if missing_headers:
                    return self._error_response(
                        f"Missing required headers: {', '.join(missing_headers)}", 
                        400
                    )
                
                # Validate API key
                api_key = request.headers.get('X-Api-Key')
                if not self._is_valid_api_key(api_key):
                    return self._error_response("Invalid API key", 401)
                
                # Track request for rate limiting
                if self._is_rate_limited(client_ip):
                    return self._error_response("Rate limit exceeded", 429)
                
                # Log request
                self._log_request(client_ip)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
        
    def _is_ip_blocked(self, ip: str) -> bool:
        return ip in self.blocked_ips or self.redis.exists(f"blocked_ip:{ip}")
        
    def _is_valid_path(self, path: str) -> bool:
        return any(re.match(pattern, path) for pattern in self.allowed_paths)
        
    def _check_required_headers(self) -> List[str]:
        return [header for header in self.required_headers 
                if header not in request.headers]
                
    def _is_valid_api_key(self, api_key: str) -> bool:
        return self.redis.exists(f"api_key:{api_key}")
        
    def _is_rate_limited(self, client_ip: str) -> bool:
        key = f"rate_limit:{client_ip}"
        count = self.redis.increment(key)
        if count == 1:
            self.redis.redis_client.expire(key, 60)  # 1 minute window
        return count > 100  # 100 requests per minute
        
    def _log_request(self, client_ip: str) -> None:
        log_data = {
            'ip': client_ip,
            'path': request.path,
            'method': request.method,
            'timestamp': datetime.utcnow().isoformat(),
            'user_agent': request.headers.get('User-Agent'),
        }
        self.redis.set(
            f"request_log:{datetime.utcnow().timestamp()}",
            log_data,
            expires_in=86400  # 24 hours
        )
        
    def _error_response(self, message: str, status_code: int) -> tuple:
        return jsonify({
            'error': message,
            'status_code': status_code,
            'timestamp': datetime.utcnow().isoformat()
        }), status_code