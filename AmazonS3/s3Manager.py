import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from io import BytesIO

class S3Manager:
    def __init__(self, region_name='eu-north-1'):
        """
        Initialize an S3 client.
        
        :param region_name: AWS region where the bucket is located.
        """
        self.region_name = region_name
        self.s3_client = self.create_s3_client()

    def get_object(self, bucket_name, key):
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return response['Body'].read()  # Return the file content
        except Exception as e:
            print(f"Error fetching object from S3: {e}")
            return None

    def create_s3_client(self):
        """
        Create an S3 client using boto3.
        
        :return: S3 client or None in case of an error.
        """
        try:
            s3_client = boto3.client('s3', region_name=self.region_name, config=boto3.session.Config(signature_version='s3v4'))
            print("S3 client created successfully.")
            return s3_client
        except (NoCredentialsError, PartialCredentialsError):
            print("Error: AWS credentials are not configured correctly.")
            return None
        except Exception as e:
            print(f"Unknown error: {e}")
            return None

    def list_bucket_objects(self, bucket_name):
        """
        List objects in a specified S3 bucket.
        
        :param bucket_name: S3 bucket name.
        :return: List of objects or an error message.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return

        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                print(f"Objects in bucket '{bucket_name}':")
                for obj in response['Contents']:
                    print(f" - {obj['Key']}")
            else:
                print(f"Bucket '{bucket_name}' is empty or does not exist.")
        except ClientError as e:
            print(f"Error accessing bucket: {e}")
        except Exception as e:
            print(f"Unknown error: {e}")

    def upload_file(self, file_path, bucket_name, object_key):
        """
        Upload a file to a specified S3 bucket.
        
        :param file_path: Local file path.
        :param bucket_name: S3 bucket name.
        :param object_key: S3 object key.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return

        try:
            self.s3_client.upload_file(file_path, bucket_name, object_key)
            print(f"File '{file_path}' uploaded to bucket '{bucket_name}' with key '{object_key}'.")
        except ClientError as e:
            print(f"Error uploading file: {e}")
        except Exception as e:
            print(f"Unknown error: {e}")

    def upload_fileobj(self, fileobj, bucket_name, object_key):
        """
        Upload a file-like object to a specified S3 bucket.
        
        :param fileobj: File-like object (e.g., from request.files).
        :param bucket_name: S3 bucket name.
        :param object_key: S3 object key.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return

        try:
            self.s3_client.upload_fileobj(fileobj, bucket_name, object_key, ExtraArgs={'ACL': 'public-read'})
            print(f"File object uploaded to bucket '{bucket_name}' with key '{object_key}'.")
        except ClientError as e:
            print(f"Error uploading file object: {e}")
        except Exception as e:
            print(f"Unknown error: {e}")

    def download_file(self, bucket_name, object_key, download_path):
        """
        Download a file from a specified S3 bucket.
        
        :param bucket_name: S3 bucket name.
        :param object_key: S3 object key.
        :param download_path: Local path to save the file.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return

        try:
            self.s3_client.download_file(bucket_name, object_key, download_path)
            print(f"File '{object_key}' downloaded to '{download_path}'.")
        except ClientError as e:
            print(f"Error downloading file: {e}")
        except Exception as e:
            print(f"Unknown error: {e}")

    def generate_presigned_url(self, bucket_name, object_key, expiration=3600):
        """
        Generate a pre-signed URL for accessing an object.
        
        :param bucket_name: S3 bucket name.
        :param object_key: S3 object key.
        :param expiration: URL expiration time in seconds.
        :return: Pre-signed URL or None if an error occurs.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return None

        try:
            response = self.s3_client.generate_presigned_url('get_object',
                                                            Params={'Bucket': bucket_name,
                                                                    'Key': object_key},
                                                            ExpiresIn=expiration)
            return response
        except ClientError as e:
            print(f"Error generating pre-signed URL: {e}")
            return None
        except Exception as e:
            print(f"Unknown error: {e}")
            return None

    def delete_file(self, bucket_name, object_key):
        """
        Delete a file from a specified S3 bucket.
        
        :param bucket_name: S3 bucket name.
        :param object_key: S3 object key.
        """
        if not self.s3_client:
            print("S3 client not created. Check credentials.")
            return

        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            print(f"File '{object_key}' deleted from bucket '{bucket_name}'.")
        except ClientError as e:
            print(f"Error deleting file: {e}")
        except Exception as e:
            print(f"Unknown error: {e}")
