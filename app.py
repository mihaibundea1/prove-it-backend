import os
from flask import Flask
from routes.posts import posts_bp
from routes.user_information import user_information_bp
from routes.credentials import credentials_bp
from routes.exercises import exercises_bp
from Database.mongo_manager import MongoDBManager
from AmazonS3.s3Manager import S3Manager
from Database.local_mysql import LocalMySQL

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

def create_databases(app):
    mongodb_username = 'mihaibundea'
    mongodb_password = 'Cluster-test'
    mongodb_cluster_url = 'cluster-develop.w8apsjm.mongodb.net'

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
            return "Connected to the local databased"
        else:
            return 'Database not connected.'
    except Exception as e:
        # e holds description of the error
        error_text = "The error:"+ str(e)
        hed = 'Something is broken.'
        return hed + error_text

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

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)