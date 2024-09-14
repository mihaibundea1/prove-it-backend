import os
from flask import Flask
from routes.posts import posts_bp
from routes.user_information import user_information_bp
from routes.credentials import credentials_bp
from Database.mongo_manager import MongoDBManager
from AmazonS3.s3Manager import S3Manager
from Database.local_mysql import LocalMySQL

# Global flag to track initialization
INITIALIZED = False

def create_app():
    global INITIALIZED
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def get_questions():
        return "Successfully connected"
    
    create_route_blueprints(app)
    
    if not INITIALIZED:
        initialize_app(app)
        INITIALIZED = True
    
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

def create_local_mysql(app):
    app.mysql_db = LocalMySQL()
    app.mysql_db.connect()
    
    if app.mysql_db.cursor:
        tables = app.mysql_db.get_table_names()
        if tables:
            print(f"Connected to MySQL. Tables: {tables}")
        else:
            print("Connected to MySQL. No tables found.")
    else:
        print("Failed to connect to MySQL database.")

    @app.teardown_appcontext
    def close_mysql_connection(exception=None):
        mysql_db = getattr(app, 'mysql_db', None)
        if mysql_db:
            mysql_db.disconnect()

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)