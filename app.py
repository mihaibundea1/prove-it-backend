# app.py
from flask import Flask
from routes.posts import posts_bp
from routes.user_information import user_information_bp
from routes.credentials import credentials_bp
from Database.mongo_manager import MongoDBManager
from AmazonS3.s3Manager import S3Manager

def create_app():
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def get_questions():
        return "Successfully connected"
    
    create_route_blueprints(app)
    create_databases(app)

    app.s3_manager = S3Manager()  # Ensure you have defined S3Manager correctly

    return app

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
        database_name='user_data'  # Ensure this is correct
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

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
