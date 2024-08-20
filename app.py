# app.py
from flask import Flask
from routes.posts import posts_bp
from routes.users import users_bp
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
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(credentials_bp, url_prefix='/credentials')

def create_databases(app):
    mongodb_username = 'mihaibundea'
    mongodb_password = 'Cluster-test'
    mongodb_cluster_url = 'cluster-develop.w8apsjm.mongodb.net'

    # Create instances of MongoDBManager
    mongo_users = MongoDBManager(
        username=mongodb_username,
        password=mongodb_password,
        cluster_url=mongodb_cluster_url,
        database_name='user_data'  # Ensure this is correct
    )
    mongo_users.test_connection()

    mongo_posts = MongoDBManager(
        username=mongodb_username,
        password=mongodb_password,
        cluster_url=mongodb_cluster_url,
        database_name='content'
    )

    mongo_credentials = MongoDBManager(
        username=mongodb_username,
        password=mongodb_password,
        cluster_url=mongodb_cluster_url,
        database_name='user_data'
    )
    mongo_posts.test_connection()
    
    app.db_users = mongo_users.get_database()
    app.db_posts = mongo_posts.get_database()
    app.db_credentials = mongo_credentials.get_database()

    

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
