# CAPT_Interface_python/login/utils.py

from django.conf import settings
from django.utils import timezone
from botocore.exceptions import ClientError
from django.conf import settings
from zoneinfo import ZoneInfo
import datetime
import boto3

def _get_dt(key_name):
    period_dates_config = settings.PERIOD_DATES
    dt_tuple = period_dates_config.get(key_name)
    if dt_tuple:
        return timezone.make_aware(datetime.datetime(*dt_tuple))

try:
    pre_start_date = _get_dt('PRE_START')
    pre_end_date = _get_dt('PRE_END')
    training_start_date_1 = _get_dt('TRAINING_START_1')
    training_end_date_1 = _get_dt('TRAINING_END_1')
    training_start_date_2 = _get_dt('TRAINING_START_2')
    training_end_date_2 = _get_dt('TRAINING_END_2')
    post_start_date = _get_dt('POST_START')
    post_end_date = _get_dt('POST_END')
    delay_start_date = _get_dt('DELAY_START')
    delay_end_date = _get_dt('DELAY_END')
except ValueError as e:
    print(f"Error creating datetime objects from settings: {e}") 

def get_current_period():

    current_time = datetime.datetime.now(ZoneInfo(settings.TIME_ZONE))

    if pre_start_date <= current_time <= pre_end_date:
        return 0
    elif training_start_date_1 <= current_time <= training_end_date_1:
        return 1
    elif training_start_date_2 <= current_time <= training_end_date_2:
        return 2
    elif post_start_date <= current_time <= post_end_date:
        return 3
    elif delay_start_date <= current_time <= delay_end_date:
        return 4
    else:
        return -1
    
def get_period_of(time):
    
    time = time.astimezone(ZoneInfo(settings.TIME_ZONE))
    
    if pre_start_date <= time <= pre_end_date:
        return 0
    elif training_start_date_1 <= time <= training_end_date_1:
        return 1
    elif training_start_date_2 <= time <= training_end_date_2:
        return 2
    elif post_start_date <= time <= post_end_date:
        return 2
    elif delay_start_date <= time <= delay_end_date:
        return 3
    else:
        return -1

def get_signed_url(file_key):
    s3_client = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME)

    try:
        s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return None
        raise

    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': file_key},
        ExpiresIn=3600  # seconds
    )