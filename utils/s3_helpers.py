from flask import current_app
from urllib.parse import urlparse, parse_qs
import bcrypt


def extract_bucket_and_key(url):
    # Descompunem URL-ul folosind urlparse
    parsed_url = urlparse(url)
    
    # Extragem query-ul din URL
    query_params = parse_qs(parsed_url.query)
    
    # Extragem `bucket_name` și `s3_key`
    bucket_name = parsed_url.path.split('/')[3]  # al 4-lea element din calea URL-ului
    s3_key = query_params.get('prefix', [None])[0]  # Extragem cheia `prefix`
    
    return bucket_name, s3_key

def generate_presigned_url(url):
    try:
        s3_manager = current_app.s3_manager
        bucket_name, s3_key = extract_bucket_and_key(url)
        
        print(bucket_name)
        print(s3_key)

        url = s3_manager.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=3600,  # Valabil pentru o oră
            HttpMethod='GET'  # Asigură că metoda HTTP este specificată
        )
        print(f'url din helper {url}')
        return url
    except AttributeError:
        print("S3 manager not found on current_app")
        return None
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
