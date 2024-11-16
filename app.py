import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from routes.posts import posts_bp
from routes.user_information import user_information_bp
from routes.credentials import credentials_bp
from routes.exercises import exercises_bp
from routes.gemini import gemini_bp
from routes.workouts import workouts_bp
from Database.mongo_manager import MongoDBManager
from AmazonS3.s3Manager import S3Manager
from Database.local_mysql import LocalMySQL
from scripts.question_updater import update_questions  
from routes.questions import questions_bp 
from core.redis_manager import RedisManager
from core.rabbitmq_manager import RabbitMQManager
from core.redis.exercises_cache_manager import ExercisesCacheManager

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def get_questions():
        return "Successfully connected"

    @app.route('/test-message-brokers')
    def test_message_brokers():
        results = {}
        
        # Test Redis
        if app.redis_manager:
            try:
                app.redis_manager.set('test_key', 'test_value')
                redis_value = app.redis_manager.get('test_key')
                results['redis'] = f"Success: {redis_value}"
            except Exception as e:
                results['redis'] = f"Error: {str(e)}"
        
        # Test RabbitMQ
        if app.rabbitmq_manager:
            try:
                app.rabbitmq_manager.publish('test_queue', 'test_message')
                results['rabbitmq'] = "Message published successfully"
            except Exception as e:
                results['rabbitmq'] = f"Error: {str(e)}"
        
        return jsonify(results)

    initialize_app(app)
    create_route_blueprints(app)
    
    return app

def initialize_app(app):
    print("Starting app initialization...")
    create_databases(app)
    create_local_mysql(app)
    app.s3_manager = S3Manager()

    initialize_message_brokers(app)
    initialize_cache_managers(app)
    print("App initialization complete.")

def initialize_cache_managers(app):
    """Initialize cache managers and preload data"""
    try:
        print("Starting cache initialization...")
        app.exercises_cache = ExercisesCacheManager()
        
        # Preîncarcă exercițiile în cache folosind S3Manager
        with app.app_context():
            total_exercises = app.exercises_cache.initialize_cache(app.s3_manager)
            print(f"Cache initialization completed with {total_exercises} exercises")
            
    except Exception as e:
        print(f"Warning: Cache initialization failed: {e}")
        app.exercises_cache = None

def initialize_message_brokers(app):
    """Initialize Redis and RabbitMQ connections"""
    # Initialize Redis
    try:
        app.redis_manager = RedisManager()
        if app.redis_manager.health_check():
            print("Redis initialization successful")
        else:
            print("Warning: Redis health check failed")
    except Exception as e:
        print(f"Warning: Redis initialization failed: {e}")
        app.redis_manager = None

    # Initialize RabbitMQ
    try:
        app.rabbitmq_manager = RabbitMQManager()
        if app.rabbitmq_manager.health_check():
            print("RabbitMQ initialization successful")
            
            # Optional: Setup default exchanges/queues
            app.rabbitmq_manager.declare_queue('default_queue', durable=True)
        else:
            print("Warning: RabbitMQ health check failed")
    except Exception as e:
        print(f"Warning: RabbitMQ initialization failed: {e}")
        app.rabbitmq_manager = None

def create_route_blueprints(app):
    app.register_blueprint(posts_bp, url_prefix='/posts')
    app.register_blueprint(user_information_bp, url_prefix='/user_information')
    app.register_blueprint(credentials_bp, url_prefix='/credentials')
    app.register_blueprint(exercises_bp, url_prefix='/exercises')
    app.register_blueprint(gemini_bp, url_prefix='/gemini')
    app.register_blueprint(workouts_bp, url_prefix='/workouts')
    app.register_blueprint(questions_bp, url_prefix='/questions')

def create_databases(app):
    mongodb_username = os.getenv('MONGODB_USERNAME')
    mongodb_password = os.getenv('MONGODB_PASSWORD')
    mongodb_cluster_url = os.getenv('MONGODB_CLUSTER_URL')

    # Create instances of MongoDBManager
    mongo_user_data = MongoDBManager(
        username=mongodb_username,
        password=mongodb_password,
        cluster_url=mongodb_cluster_url,
        database_name='user_data'
    )

    mongo_content = MongoDBManager(
        username=mongodb_username,
        password=mongodb_password,
        cluster_url=mongodb_cluster_url,
        database_name='content'
    )

    mongo_user_data.test_connection()
    mongo_content.test_connection()
    
    app.user_data = mongo_user_data.get_database()
    app.db_content = mongo_content.get_database()

def create_local_mysql(app):
    app.mysql_db = LocalMySQL(
            host='127.0.0.1',      
            port=3308,            
            user='exercises',       
            password='exercises1!',
            database='exercises'
        )
    print(testdb(app))

def testdb(app):
    try:
        if app.mysql_db.is_connected():
            app.mysql_db.execute_query("SELECT 1")
            return "Connected to the local database"
        else:
            return 'Database not connected.'
    except Exception as e:
        error_text = "The error:" + str(e)
        return 'Something is broken. ' + error_text

# Cleanup function for graceful shutdown
def cleanup_connections(app):
    """Cleanup all connections when shutting down"""
    if hasattr(app, 'redis_manager'):
        try:
            app.redis_manager.get_connection().close()
        except:
            pass

    if hasattr(app, 'rabbitmq_manager'):
        try:
            app.rabbitmq_manager.close()
        except:
            pass

    if hasattr(app, 'exercises_cache'):
        try:
            app.exercises_cache.clear_exercise_cache()
        except:
            pass

if __name__ == '__main__':
    app = create_app()
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        cleanup_connections(app)