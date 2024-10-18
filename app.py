import os
from flask import Flask
from dotenv import load_dotenv
from routes.posts import posts_bp
from routes.user_information import user_information_bp
from routes.credentials import credentials_bp
from routes.exercises import exercises_bp
from routes.gemini import gemini_bp
from Database.mongo_manager import MongoDBManager
from AmazonS3.s3Manager import S3Manager
from Database.local_mysql import LocalMySQL

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def get_questions():
        return "Successfully connected"
    
    initialize_app(app)
    create_route_blueprints(app)
    
    return app

def initialize_app(app):
    print("Starting app initialization...")
    create_databases(app)
    create_local_mysql(app)
    app.s3_manager = S3Manager()
    print("App initialization complete.")

def create_route_blueprints(app):
    app.register_blueprint(posts_bp, url_prefix='/posts')
    app.register_blueprint(user_information_bp, url_prefix='/user_information')
    app.register_blueprint(credentials_bp, url_prefix='/credentials')
    app.register_blueprint(exercises_bp, url_prefix='/exercises')
    app.register_blueprint(gemini_bp, url_prefix='/gemini')

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

def testdb(app):
    try:
        # Access LocalMySQL instance from the app object
        if app.mysql_db.is_connected():
            app.mysql_db.execute_query("SELECT 1")
            return "Connected to the local database"
        else:
            return 'Database not connected.'
    except Exception as e:
        # e holds description of the error
        error_text = "The error:" + str(e)
        return 'Something is broken. ' + error_text

def create_local_mysql(app):
    # Initialize LocalMySQL with parameters
    app.mysql_db = LocalMySQL(
        host='localhost',
        port=3308,
        user='exercises',
        password='exercises1!',
        database='exercises'
    )
    print(testdb(app))

# Gemini API Key
gemini_api_key = os.getenv('GEMINI_API_KEY')

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
