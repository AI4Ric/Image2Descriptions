from storages.backends.s3boto3 import S3Boto3Storage
import os

class StaticStorage(S3Boto3Storage):
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME_STATIC')
    custom_domain = f'{bucket_name}.s3.amazonaws.com'
