import mysql.connector
from mysql.connector import Error

class LocalMySQL:
    def __init__(self, host='localhost', port=3308, user='exercises', password='exercises1!', database='exercises'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                collation='utf8mb4_general_ci'
            )
            if self.connection.is_connected():
                self.cursor = self.connection.cursor()
                print(f"Connected to MySQL database: {self.database}")
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
            self.connection = None
            self.cursor = None

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            print("MySQL connection is closed")

    def execute_query(self, query):
        if not self.cursor:
            print("Not connected to the database. Call connect() first.")
            return
        try:
            self.cursor.execute(query)
            self.connection.commit()
            print("Query executed successfully")
        except Error as e:
            print(f"Error executing query: {e}")

    def fetch_all(self, query):
        if not self.cursor:
            print("Not connected to the database. Call connect() first.")
            return None
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Error as e:
            print(f"Error fetching data: {e}")
            return None

    def get_table_names(self):
        if not self.cursor:
            print("Not connected to the database. Call connect() first.")
            return None
        try:
            self.cursor.execute("SHOW TABLES")
            return [table[0] for table in self.cursor.fetchall()]
        except Error as e:
            print(f"Error fetching table names: {e}")
            return None