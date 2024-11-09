from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pymysql

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
            self.engine = create_engine(
                f'mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}',
                pool_pre_ping=True
            )
            print("SQLAlchemy engine created")
        except SQLAlchemyError as e:
            print(f"Error creating SQLAlchemy engine: {e}")
            raise

    def execute_query(self, query, params=None):
        try:
            with self.engine.connect() as connection:
                if isinstance(query, str):
                    query = text(query)
                
                if params:
                    # Convert tuple params to dict for SQLAlchemy
                    if isinstance(params, tuple):
                        # Create placeholders for the parameters
                        param_dict = {}
                        for i, value in enumerate(params):
                            param_dict[f'param_{i}'] = value
                        # Replace %s with :param_0, :param_1, etc.
                        modified_query = query.text
                        for i in range(len(params)):
                            modified_query = modified_query.replace('%s', f':param_{i}', 1)
                        query = text(modified_query)
                        result = connection.execute(query, param_dict)
                    else:
                        result = connection.execute(query, params)
                else:
                    result = connection.execute(query)
                
                if query.text.strip().upper().startswith('SELECT'):
                    return [dict(row._mapping) for row in result]
                else:
                    connection.commit()
                    return True
                    
        except SQLAlchemyError as e:
            print(f"Error executing query: {e}")
            raise

    def is_connected(self):
        try:
            if self.engine:
                with self.engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                return True
            return False
        except SQLAlchemyError:
            return False

    def close(self):
        if self.engine:
            self.engine.dispose()