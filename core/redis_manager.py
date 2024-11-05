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

class RedisManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'RedisManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def __init__(self):
        """Prevent re-initialization of the singleton"""
        pass
        
    def _initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            load_dotenv()
            
            # Docker connection details
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,  # Automatically decode responses to str
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            self.default_ttl = 3600
            self.logger = logging.getLogger(__name__)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connection: {e}")
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
            
            # Set expiration
            if isinstance(expires_in, timedelta):
                expires_in = int(expires_in.total_seconds())
            elif expires_in is None:
                expires_in = self.default_ttl
                
            return self.redis_client.set(
                key, 
                serialized_value,
                ex=expires_in,
                nx=nx
            )
            
        except Exception as e:
            self.logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def get(self, 
            key: str, 
            default: Any = None, 
            deserialize: bool = True) -> Any:
        """Get a value from Redis"""
        try:
            result = self.redis_client.get(key)
            
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
            return self.redis_client.ping()
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False
            
    def clear_cache(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
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
            pipeline = self.redis_client.pipeline()
            pipeline.incrby(key, amount)
            if expires_in:
                pipeline.expire(key, expires_in)
            results = pipeline.execute()
            return results[0]
            
        except Exception as e:
            self.logger.error(f"Redis atomic increment error for key {key}: {e}")
            return None
            
    @contextmanager
    def get_connection(self):
        """Context manager for connection handling"""
        try:
            yield self.redis_client
        except Exception as e:
            self.logger.error(f"Redis connection error: {e}")
            raise