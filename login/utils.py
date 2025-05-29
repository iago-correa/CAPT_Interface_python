# CAPT_Interface_python/login/utils.py

from django.conf import settings
from django.utils import timezone
import datetime

def get_current_period():
    """
    Determines the current experiment period based on dates in settings.py.
    Returns:
        int: Period code (0 for Pre, 1 for Training, 2 for Post, 3 for Delay, -1 for outside any period).
    """
    period_dates_config = settings.PERIOD_DATES

    # Create timezone-aware datetime objects from config tuples
    def _get_dt(key_name):
        dt_tuple = period_dates_config.get(key_name)
        if dt_tuple:
            return timezone.make_aware(datetime.datetime(*dt_tuple))

    try:
        pre_start_date = _get_dt('PRE_START')
        pre_end_date = _get_dt('PRE_END')
        training_start_date = _get_dt('TRAINING_START')
        training_end_date = _get_dt('TRAINING_END')
        post_start_date = _get_dt('POST_START')
        post_end_date = _get_dt('POST_END')
        delay_start_date = _get_dt('DELAY_START')
        delay_end_date = _get_dt('DELAY_END')
    except ValueError as e:
        print(f"Error creating datetime objects from settings: {e}") 
        return -2 

    current_time = timezone.now()

    if pre_start_date <= current_time <= pre_end_date:
        return 0
    elif training_start_date <= current_time <= training_end_date:
        return 1
    elif post_start_date <= current_time <= post_end_date:
        return 2
    elif delay_start_date <= current_time <= delay_end_date:
        return 3
    else:
        return -1