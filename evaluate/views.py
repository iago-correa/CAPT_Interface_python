from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings

from login.utils import get_signed_url
from login.models import Student, Session 
from practice.models import Activity
from record.models import Recording
from .models import Evaluation

from urllib.parse import urlencode
import datetime
import random

try:
    period_dates_config = settings.PERIOD_DATES
    PERIODS_CONFIG = [
        {
            'name': '1. Pre-training Recording',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('PRE_START'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('PRE_END'))),
            'activity_type': 'test_pre_record',
            'count_types': ['test_nat'] # Count this audio type
        },
        {
            'name': '2. Training Session 1',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_START_1'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_END_1'))),
            'activity_type': 'train_record',
            'count_types': ['train_nat', 'train_gs'] # Count these types separately
        },
        {
            'name': '3. Training Session 2',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_START_2'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_END_2'))),
            'activity_type': 'train_record',
            'count_types': ['train_nat', 'train_gs'] # Count these types separately
        },
        {
            'name': '4. Post-training Recording',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('POST_START'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('POST_END'))),
            'activity_type': 'test_post_record',
            'count_types': ['test_nat']
        },
        {
            'name': '5. Delayed Recording',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('DELAY_START'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('DELAY_END'))),
            'activity_type': 'test_delay_record',
            'count_types': ['test_nat'] 
        }
    ]
except (AttributeError, TypeError):
    # Fallback if settings.PERIOD_DATES is not configured, prevents crashing
    PERIODS_CONFIG = []

def get_students_to_evaluate(target_period=5):
    
    ignored_ids = settings.IGNORED_STUDENTS
    
    previous_students = set()
    message = ""

    for i, period in enumerate(PERIODS_CONFIG):
        period_name = period['name']
        start_time = period['start_time'].replace(tzinfo=None)
        end_time = period['end_time'].replace(tzinfo=None)
        audio_type = period['count_types']
        completion_target = 20

        completed_students = set()

        # Fetch current period completions
        completions_qs = Activity.objects.filter(
            time__range=(start_time, end_time),
            recording__isnull=False,
            recording__original_audio__type__in=audio_type,
        ).exclude(
            session__student__id__in=ignored_ids
        ).values(
            'session__student',
            'session__student__control_group'
        ).annotate(
            unique_recordings=Count('recording__original_audio', distinct=True)
        ).filter(
            unique_recordings=completion_target
        )
        
        if i > 0:
            completions_qs = completions_qs.filter(session__student__id__in=previous_students)

        for entry in completions_qs:
            student_id = entry['session__student']
            completed_students.add(student_id)
        
        message += f"{period_name}: {len(completed_students)} students."

        if(i+1==target_period):
            return completed_students, message
        
        previous_students = completed_students

@csrf_exempt
def evaluate(request):
    
    session_id = request.session.get('session_id')
    
    if not session_id:
        error_message = 'Please sign in.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:evaluation_login')}?{query_params}")

    try:
        session_obj = Session.objects.get(id=session_id)
        rater = session_obj.rater
    except Session.DoesNotExist:
        request.session.flush()
        error_message = 'The session is not active anymore, plase sign in again.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:evaluation_login')}?{query_params}")
    
    if request.method == 'GET':
        
        evaluation_set = []
        
        students_to_evaluate, debug_text = get_students_to_evaluate(4)
        
        # All the evaluations of the current rater
        completed_evaluations = Evaluation.objects.filter(
            session__rater = rater
        )
        num_completed = len(completed_evaluations)
        
        # Select all recordings for the experiment students
        activities = Activity.objects.filter(
            session__student__in=students_to_evaluate,
            type__in=['test_pre_record', 'test_post_record', 'test_delay_record']
        ).select_related('recording')
        num_total = len(activities)
        
        # From all the recordings, pick the ones not evaluated
        activities = activities.exclude(recording__in=completed_evaluations.values_list('recording', flat=True))
        
        for activity in activities:
            recording = activity.recording
            file_key = f"{settings.MEDIA_ROOT}{recording.recorded_audio.name}"
            recording_signed_url = get_signed_url(file_key)
            
            evaluation_set.append([recording, recording_signed_url])
        
        if num_total > 0:
            completion = int(100*num_completed/num_total)
        else:
            completion = 0
        
        if(len(evaluation_set) >= 5):
            evaluation_set = random.sample(evaluation_set, 5)
        
        context_data = {
            'scores': range(10),
            'num_completed': num_completed,
            'num_total': num_total,
            'completion': completion,
            'evaluation_set': evaluation_set, 
            'debug_text': debug_text,
            'csrf_token_value': request.META.get('CSRF_COOKIE')
        }

        if(num_completed==num_total):
            if(num_total == 0):
                context_data['error'] = "No files found."
            else:
                context_data['success'] = "All files have been evaluated."
                  
        return render(request, 'evaluate/evaluate.html', context_data)
    
    elif request.method == "POST":
        
        session = Session.objects.get(id = request.session['session_id'])
        
        for key in request.POST:
            if key.startswith('problem-check'):
                
                recording_id = key.split('-')[-1]
                recording = Recording.objects.get(id = recording_id)
                
                evualuation_score = request.POST.get('score-radio-'+str(recording_id), 0)
                evaluation_problem = request.POST.get(key, False)
        
                Evaluation.objects.update_or_create(
                    defaults={'session': session,
                            'score': evualuation_score,
                            'problem': evaluation_problem}, 
                    recording=recording
                )
                
            if key.startswith('score-radio'):
                
                recording_id = key.split('-')[-1]
                recording = Recording.objects.get(id = recording_id)
                
                evualuation_score = request.POST[key]
                evaluation_problem = request.POST.get('problem-check-'+str(recording_id), False)
        
                Evaluation.objects.update_or_create(
                    defaults={'session': session,
                            'score': evualuation_score,
                            'problem': evaluation_problem}, 
                    recording=recording
                )
        
        return redirect('evaluate:evaluate')
    