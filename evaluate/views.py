from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError 

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
        
def update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem):
    
    evaluation_data = {
        'score': evaluation_score,
        'problem': evaluation_problem
    }
    
    try:
        target_rater_for_evaluation = session.rater # This is the specific rater we care about for uniqueness
    except Recording.DoesNotExist:
        return JsonResponse({'error': 'Recording not found.'}, status=404)
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)

    try:
        with transaction.atomic():
            # Query if a register with recording + session__rater already exists
            try:
                evaluation_instance = Evaluation.objects.get(
                    recording=recording,
                    session__rater=target_rater_for_evaluation
                )
                # If it exists, update it
                for field, value in evaluation_data.items():
                    setattr(evaluation_instance, field, value)

                evaluation_instance.save() 
                created = False
                message = "Evaluation updated successfully."

            except Evaluation.DoesNotExist:
                # If it does not exist, call create a new
                evaluation_instance = Evaluation(
                    recording=recording,
                    session=session,
                    **evaluation_data
                )
                evaluation_instance.save()
                created = True
                message = "Evaluation created successfully."

        # Return a success response
        return JsonResponse({
            'message': message,
            'evaluation_id': evaluation_instance.id,
            'created': created
        }, status=200 if not created else 201)

    except ValidationError as e:
        return JsonResponse({'error': e.message_dict}, status=400)
    except Exception as e:    
        return JsonResponse({'error': str(e)}, status=500)


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
        # students_to_evaluate = Student.objects.all()
        
        # All the recordings that were evaluated by the current rater
        completed_recording_ids = Evaluation.objects.filter(
            session__rater=rater
        ).values_list('recording_id', flat=True) # Only fetch the IDs

        # Select the relavant activities
        relevant_activities = Activity.objects.filter(
            session__student__in=students_to_evaluate,
            type__in=['test_pre_record', 'test_post_record', 'test_delay_record']
        ).exclude(
            # Exclude activities whose recordings have already been evaluated by the current rater
            recording_id__in=completed_recording_ids
        ).select_related('recording').values('recording__id', 'recording__recorded_audio', 'recording__original_audio__transcript').order_by("?")[:5]

        evaluation_set = []

        for activity in relevant_activities.iterator():
            if activity['recording__id']:
                file_key = f"{settings.MEDIA_ROOT}{activity['recording__recorded_audio']}"
                recording_signed_url = get_signed_url(file_key)
                evaluation_set.append(
                    [activity['recording__id'], 
                     activity['recording__recorded_audio'], 
                     activity['recording__original_audio__transcript'], 
                     recording_signed_url])

        num_completed = Evaluation.objects.filter(session__rater=rater).count()
        num_total = Activity.objects.filter(
            session__student__in=students_to_evaluate,
            type__in=['test_pre_record', 'test_post_record', 'test_delay_record']
        ).count() 
        
        if num_total > 0:
            completion = int(100*num_completed/num_total)
        else:
            completion = 0
        
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
                
                evaluation_score = request.POST.get('score-radio-'+str(recording_id), 0)
                evaluation_problem = request.POST.get(key, False)
        
                update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem)
                
            if key.startswith('score-radio'):
                
                recording_id = key.split('-')[-1]
                recording = Recording.objects.get(id = recording_id)
                
                evaluation_score = request.POST[key]
                evaluation_problem = request.POST.get('problem-check-'+str(recording_id), False)
        
                update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem)
        
        return redirect('evaluate:evaluate')
    