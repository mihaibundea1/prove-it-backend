import redis
from typing import Optional, Any, Union
import json
from datetime import timedelta
import threading
from contextlib import contextmanager
import logging
from redis.exceptions import ConnectionError, TimeoutError
import os
from dotenv import load_dotenv
import requests
from urllib.parse import quote

class RedisManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'RedisManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.logger = logging.getLogger(__name__)
                    cls._instance._initialize()

        return cls._instance
    
    def __init__(self):
        """Prevent re-initialization of the singleton"""
        pass
        
    def _initialize(self) -> None:
        """Initialize connection details"""
        try:
            load_dotenv()
            
            self.redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
            self.redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
            
            if not self.redis_url or not self.redis_token:
                raise ValueError("Missing Upstash Redis credentials")
            
            self.headers = {
                'Authorization': f'Bearer {self.redis_token}'
            }
            
            self.default_ttl = 3600
            self.logger = logging.getLogger(__name__)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    def _make_request(self, command: list) -> Any:
        """Make a request to Upstash Redis"""
        try:
            # Encode command for URL
            encoded_command = "/".join(quote(str(arg)) for arg in command)
            url = f"{self.redis_url}/{encoded_command}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('result')
            
        except Exception as e:
            self.logger.error(f"Redis request failed: {e}")
            raise
    
    def set(self, 
            key: str, 
            value: Any, 
            expires_in: Optional[Union[int, timedelta]] = None,
            nx: bool = False) -> bool:
        """Set a value in Redis"""
        try:
            # Serialize value
            serialized_value = (
                json.dumps(value) 
                if not isinstance(value, (str, int, float)) 
                else str(value)
            )
            
            # Build command
            command = ["SET", key, serialized_value]
            
            # Add expiration
            if expires_in:
                if isinstance(expires_in, timedelta):
                    expires_in = int(expires_in.total_seconds())
                command.extend(["EX", str(expires_in)])
            elif self.default_ttl:
                command.extend(["EX", str(self.default_ttl)])
            
            # Add NX if requested
            if nx:
                command.append("NX")
            
            result = self._make_request(command)
            return result == "OK"
            
        except Exception as e:
            self.logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def get(self, 
            key: str, 
            default: Any = None, 
            deserialize: bool = True) -> Any:
        """Get a value from Redis"""
        try:
            result = self._make_request(["GET", key])
            
            if result is None:
                return default
            
            if deserialize:
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return result
            return result
            
        except Exception as e:
            self.logger.error(f"Redis get error for key {key}: {e}")
            return default
    
    def health_check(self) -> bool:
        """Perform a health check"""
        try:
            result = self._make_request(["PING"])
            return result == "PONG"
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
            
    def clear_cache(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        try:
            keys = self._make_request(["KEYS", pattern])
            if keys and isinstance(keys, list):
                deleted = 0
                for key in keys:
                    if self._make_request(["DEL", key]):
                        deleted += 1
                return deleted
            return 0
        except Exception as e:
            self.logger.error(f"Redis clear cache error for pattern {pattern}: {e}")
            return 0
    
    def atomic_increment(self, 
                        key: str, 
                        amount: int = 1, 
                        expires_in: Optional[int] = None) -> Optional[int]:
        """Atomically increment a counter"""
        try:
            # Increment
            new_value = self._make_request(["INCRBY", key, str(amount)])
            
            # Set expiration if needed
            if expires_in:
                self._make_request(["EXPIRE", key, str(expires_in)])
                
            return new_value
            
        except Exception as e:
            self.logger.error(f"Redis atomic increment error for key {key}: {e}")
            return None
            
    @contextmanager
    def get_connection(self):
        """Context manager for compatibility"""
        try:
            yield self
        except Exception as e:
            self.logger.error(f"Redis connection error: {e}")
            raise