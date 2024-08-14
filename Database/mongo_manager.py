from pymongo import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

class MongoDBManager:
    def __init__(self, username, password, cluster_url, database_name):
        # Encodează username și password pentru a se potrivi URI-ului
        self.username = quote_plus(username)
        self.password = quote_plus(password)
        self.cluster_url = cluster_url
        self.database_name = database_name
        self.uri = f'mongodb+srv://{self.username}:{self.password}@{self.cluster_url}/?retryWrites=true&w=majority'
        # Creează clientul MongoDB
        self.client = MongoClient(self.uri, server_api=ServerApi('1'))
        # Selectează baza de date
        self.db = self.client[self.database_name]
    
    def test_connection(self):
        try:
            # Trimite un ping pentru a confirma conexiunea
            self.client.admin.command('ping')
            print(f"Pinged your deployment {self.database_name}. You successfully connected to MongoDB!")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def get_database(self):
        return self.db

    def get_database_name(self):
        """
        Returnează numele bazei de date.
        """
        return self.database_name 