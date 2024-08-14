import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

class S3Manager:
    def __init__(self, region_name='us-east-1'):
        """
        Initializează un client S3.
        
        :param region_name: Regiunea AWS în care se află bucket-ul.
        """
        self.region_name = region_name
        self.s3_client = self.create_s3_client()

    def create_s3_client(self):
        """
        Creează un client S3 folosind boto3.
        
        :return: Clientul S3 sau None în caz de eroare.
        """
        try:
            s3_client = boto3.client('s3', region_name=self.region_name)
            print("Client S3 creat cu succes.")
            return s3_client
        except (NoCredentialsError, PartialCredentialsError):
            print("Eroare: Acreditivele AWS nu sunt configurate corect.")
            return None
        except Exception as e:
            print(f"Eroare necunoscută: {e}")
            return None

    def list_bucket_objects(self, bucket_name):
        """
        Listează obiectele dintr-un bucket S3 specificat.
        
        :param bucket_name: Numele bucket-ului S3.
        :return: Lista obiectelor sau un mesaj de eroare.
        """
        if not self.s3_client:
            print("Clientul S3 nu a fost creat. Verifică acreditivele.")
            return

        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                print(f"Obiecte în bucket-ul '{bucket_name}':")
                for obj in response['Contents']:
                    print(f" - {obj['Key']}")
            else:
                print(f"Bucket-ul '{bucket_name}' este gol sau nu există.")
        except ClientError as e:
            print(f"Eroare la accesarea bucket-ului: {e}")
        except Exception as e:
            print(f"Eroare necunoscută: {e}")

    def upload_file(self, file_path, bucket_name, object_key):
        """
        Încarcă un fișier într-un bucket S3 specificat.
        
        :param file_path: Calea fișierului local.
        :param bucket_name: Numele bucket-ului S3.
        :param object_key: Cheia obiectului în S3.
        """
        if not self.s3_client:
            print("Clientul S3 nu a fost creat. Verifică acreditivele.")
            return

        try:
            self.s3_client.upload_file(file_path, bucket_name, object_key)
            print(f"Fișierul '{file_path}' a fost încărcat în bucket-ul '{bucket_name}' cu cheia '{object_key}'.")
        except ClientError as e:
            print(f"Eroare la încărcarea fișierului: {e}")
        except Exception as e:
            print(f"Eroare necunoscută: {e}")

    def download_file(self, bucket_name, object_key, download_path):
        """
        Descarcă un fișier dintr-un bucket S3 specificat.
        
        :param bucket_name: Numele bucket-ului S3.
        :param object_key: Cheia obiectului în S3.
        :param download_path: Calea locală unde să fie salvat fișierul.
        """
        if not self.s3_client:
            print("Clientul S3 nu a fost creat. Verifică acreditivele.")
            return

        try:
            self.s3_client.download_file(bucket_name, object_key, download_path)
            print(f"Fișierul '{object_key}' a fost descărcat în '{download_path}'.")
        except ClientError as e:
            print(f"Eroare la descărcarea fișierului: {e}")
        except Exception as e:
            print(f"Eroare necunoscută: {e}")
