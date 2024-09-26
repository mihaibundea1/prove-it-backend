from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pymysql
from flask import jsonify
from datetime import datetime

class LocalMySQL:
    def __init__(self, host='localhost', port=3008, user='exercises', password='exercises1!', database='exercises'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.engine = None
        self.create_engine()

    def create_engine(self):
        try:
            # Construct the SQLAlchemy URI
            self.engine = create_engine(f'mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}')
            print("SQLAlchemy engine created")
            
            # Test the connection and execute a query
            with self.engine.connect() as connection:
                result = connection.execute(text("SHOW TABLES"))
                tables = result.fetchall()
                print("Tables:", tables)
        
        except SQLAlchemyError as e:
            print(f"Error creating SQLAlchemy engine or executing query: {e}")

    def is_connected(self):
        try:
            if self.engine:
                # Test the connection
                with self.engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                return True
            return False
        except SQLAlchemyError:
            return False

    def execute_query(self, query):
        print(query)
        if not self.is_connected():
            print("Not connected to the database. Please call create_engine() first.")
            return
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                return result.fetchall()
        except SQLAlchemyError as e:
            print(f"Error executing query: {e}")
            return None

    def serialize_result(self, result):
        """Convert SQLAlchemy result to a JSON-serializable format."""
        return [dict(row) for row in result]