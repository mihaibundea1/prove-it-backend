from flask import current_app

def generate_presigned_url(bucket_name, s3_key):
    try:
        s3_manager = current_app.s3_manager
        url = s3_manager.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=3600,  # Valabil pentru o oră
            HttpMethod='GET'  # Asigură că metoda HTTP este specificată
        )
        return url
    except AttributeError:
        print("S3 manager not found on current_app")
        return None
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None
