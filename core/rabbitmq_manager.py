import pika
from typing import Optional, Callable, Any
import json
import threading
from contextlib import contextmanager
import logging
import os
from dotenv import load_dotenv
from functools import wraps
import time

class RabbitMQManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'RabbitMQManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def __init__(self):
        pass
        
    def _initialize(self) -> None:
        """Initialize RabbitMQ connection"""
        try:
            load_dotenv()
            
            # Connection parameters
            self.parameters = pika.ConnectionParameters(
                host=os.getenv('RABBITMQ_HOST', 'localhost'),
                port=int(os.getenv('RABBITMQ_PORT', 5672)),
                virtual_host=os.getenv('RABBITMQ_VHOST', '/'),
                credentials=pika.PlainCredentials(
                    username=os.getenv('RABBITMQ_USER', 'guest'),
                    password=os.getenv('RABBITMQ_PASSWORD', 'guest')
                ),
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.logger = logging.getLogger(__name__)
            self._connection = None
            self._channel = None
            
            # Test connection on initialization
            self._connect()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RabbitMQ connection: {e}")
            raise

    def ensure_connection(f):
        """Decorator to ensure connection is active"""
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if not self._connection or self._connection.is_closed:
                self._connect()
            if not self._channel or self._channel.is_closed:
                self._create_channel()
            return f(self, *args, **kwargs)
        return wrapper
    
    def _connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            self._connection = pika.BlockingConnection(self.parameters)
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
            
    def _create_channel(self) -> None:
        """Create a channel"""
        if not self._connection or self._connection.is_closed:
            self._connect()
        self._channel = self._connection.channel()
    
    @ensure_connection
    def declare_queue(self, 
                     queue_name: str,
                     durable: bool = True,
                     arguments: Optional[dict] = None) -> None:
        """Declare a queue"""
        try:
            self._channel.queue_declare(
                queue=queue_name,
                durable=durable,
                arguments=arguments
            )
        except Exception as e:
            self.logger.error(f"Failed to declare queue {queue_name}: {e}")
            raise
    
    @ensure_connection
    def publish(self,
                queue_name: str,
                message: Any,
                persistent: bool = True) -> bool:
        """Publish a message to a queue"""
        try:
            # Ensure queue exists
            self.declare_queue(queue_name)
            
            # Serialize message if needed
            if not isinstance(message, str):
                message = json.dumps(message)
                
            # Publish message
            properties = pika.BasicProperties(
                delivery_mode=2 if persistent else 1  # Make message persistent
            )
            
            self._channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=properties
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish to {queue_name}: {e}")
            return False
    
    @ensure_connection
    def consume(self,
                queue_name: str,
                callback: Callable,
                auto_ack: bool = False) -> None:
        """Start consuming messages from a queue"""
        try:
            # Ensure queue exists
            self.declare_queue(queue_name)
            
            # Start consuming
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            
            self.logger.info(f"Started consuming from {queue_name}")
            self._channel.start_consuming()
            
        except Exception as e:
            self.logger.error(f"Failed to start consuming from {queue_name}: {e}")
            raise
            
    def health_check(self) -> bool:
        """Perform a health check"""
        try:
            if self._connection and not self._connection.is_closed:
                return True
            self._connect()
            return True
        except Exception as e:
            self.logger.error(f"RabbitMQ health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the connection"""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception as e:
            self.logger.error(f"Failed to close RabbitMQ connection: {e}")
            
    @contextmanager
    def get_channel(self):
        """Context manager for channel handling"""
        try:
            if not self._connection or self._connection.is_closed:
                self._connect()
            channel = self._connection.channel()
            yield channel
        except Exception as e:
            self.logger.error(f"Channel error: {e}")
            raise
        finally:
            if channel and not channel.is_closed:
                channel.close()