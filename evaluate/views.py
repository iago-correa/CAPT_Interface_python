from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError 
from django.contrib import messages

from login.utils import get_signed_url
from login.models import Student, Session 
from practice.models import Activity, Audio
from record.models import Recording
from .models import Evaluation

from urllib.parse import urlencode
import datetime
import os

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

PICKED_SENTENCES = {
    'audio/U1_reading_speaker00_t11_s1.mp3', 
    'audio/U2_presentation_speaker00_t6_s1.mp3',
    'audio/U1_reading_speaker00_t25_s1.mp3',
    'audio/U2_presentation_speaker00_t4_s1.mp3',
    'audio/U1_presentation_speaker00_t8_s1.mp3',
    'audio/U1_reading_speaker00_t24_s1.mp3',
    'audio/U2_reading_speaker00_t22_s1.mp3',
    'audio/U2_reading_speaker00_t20_s1.mp3',
    'audio/U1_authentic_conversations_speaker01_t18_s1.mp3',
    'audio/U1_presentation_speaker00_t10_s1.mp3'
}

def is_authorized(rater, part_number):
    
    part1_raters = settings.EVAL_PART1_RATERS
    part2_raters = settings.EVAL_PART2_RATERS
    part3_raters = settings.EVAL_PART3_RATERS
    
    permissions={
        1: rater.id in part1_raters,
        2: rater.id in part2_raters,
        3: rater.id in part3_raters
    }
    
    if permissions[part_number]:
        return True
    else:
        return False

def is_part_completed(rater, part_number):
    
    parts_proportions = settings.PARTS_PROPORTIONS
    
    count = Evaluation.objects.filter(
        session__rater=rater,
        part = part_number
    ).aggregate(Count('id'))['id__count']
    
    if part_number == 1 and count == parts_proportions[0]:
        return True
    elif part_number == 2 and count == parts_proportions[1]:
        return True
    elif part_number == 3 and count == parts_proportions[2]:
        return True
    else:
        return False

def get_unique_recordings_students(period_index, student_ids):
    
    relevant_activities = Activity.objects.none()
    
    for t in range(0, period_index):
        if t not in [1,2]:
            selected_period_index = t
            period = PERIODS_CONFIG[selected_period_index]

            start = period['start_time'].replace(tzinfo=None)
            end = period['end_time'].replace(tzinfo=None)
            act_type = period['activity_type']
            
            all_activities = Activity.objects.filter(
                session__student__in=student_ids, 
                time__range=(start, end)
            ).values(
                'recording__id', 
                'recording__recorded_audio', 
                'recording__original_audio__transcript'
            ).order_by('time')
            
            filtered_activities = all_activities.filter(type=act_type)
            
            relevant_activities = relevant_activities | filtered_activities

    return relevant_activities

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
        
def update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem, evaluation_part):
    
    evaluation_data = {
        'score': evaluation_score,
        'problem': evaluation_problem,
        'part': evaluation_part
    }
    
    try:
        target_rater_for_evaluation = session.rater 
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
def evaluate(request, part_number):
    
    session_id = request.session.get('session_id')
    target_session = 4 # It should be 4 for deploy
    
    normalized_paths = [os.path.join(*s.split('/')) for s in PICKED_SENTENCES]
    picked_sentences = Audio.objects.filter(file__in=normalized_paths)
    parts_proportions = settings.PARTS_PROPORTIONS
    
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
    
    if not is_authorized(rater, part_number):
        error_message = 'This part is not available yet.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('evaluate:select_part')}?{query_params}")
    if is_part_completed(rater, part_number):
        message = 'This part is already complete.'
        query_params = urlencode({'success': message})
        return redirect(f"{reverse('evaluate:select_part')}?{query_params}")
    
    if request.method == 'GET':
        
        evaluation_set = []
        
        students_to_evaluate, debug_text = get_students_to_evaluate(target_session) 
        # students_to_evaluate = {1 ,67}
        
        # All the recordings that were evaluated by the current rater
        completed_recording_ids = Evaluation.objects.filter(
            session__rater=rater,
            part=part_number
        ).values_list('recording_id', flat=True) # Only fetch the IDs\
        num_completed_recordings = len(completed_recording_ids)
        
        previously_completed_recordings_ids = Evaluation.objects.filter(
            session__rater=rater
        ).values_list('recording_id', flat=True) 
        
        relevant_activities = get_unique_recordings_students(target_session, students_to_evaluate)
        relevant_activities = relevant_activities.filter(recording__original_audio__in=picked_sentences)
        relevant_activities = relevant_activities.exclude(recording_id__in=completed_recording_ids)
        relevant_activities = relevant_activities.exclude(recording_id__in=previously_completed_recordings_ids)
        
        if part_number == 1:
            num_total = parts_proportions[0]
            relevant_activities = relevant_activities[:parts_proportions[0]-num_completed_recordings]
        elif part_number == 2:
            num_total = parts_proportions[1]
            relevant_activities = relevant_activities[:parts_proportions[1]-num_completed_recordings]
        elif part_number ==3 :
            num_total = parts_proportions[2]
            relevant_activities = relevant_activities[:parts_proportions[2]-num_completed_recordings]
        
        # Reduce number to show at once
        number_show = 5
        relevant_activities = relevant_activities[:number_show]

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
        
        if num_total > 0:
            completion = int(100*num_completed_recordings/num_total)
        else:
            completion = 0
        
        context_data = {
            'scores': range(10),
            'num_completed': num_completed_recordings,
            'num_total': num_total,
            'completion': completion,
            'evaluation_set': evaluation_set, 
            'debug_text': debug_text,
            'csrf_token_value': request.META.get('CSRF_COOKIE')
        }

        if(num_completed_recordings==num_total):
            if(num_total == 0):
                context_data['error'] = "No files found."
            else:
                context_data['success'] = "All files have been evaluated."
                 
        
        return render(request, 'evaluate/evaluate.html', context_data) 
        # return render(request, 'evaluate/evaluate.html', context_data)
    
    elif request.method == "POST":
        
        session = Session.objects.get(id = request.session['session_id'])
        
        for key in request.POST:
            if key.startswith('problem-check'):
                
                recording_id = key.split('-')[-1]
                recording = Recording.objects.get(id = recording_id)
                
                evaluation_score = request.POST.get('score-radio-'+str(recording_id), 0)
                evaluation_problem = request.POST.get(key, False)
                evaluation_part = part_number
        
                update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem, evaluation_part)
                
            if key.startswith('score-radio'):
                
                recording_id = key.split('-')[-1]
                recording = Recording.objects.get(id = recording_id)
                
                evaluation_score = request.POST[key]
                evaluation_problem = request.POST.get('problem-check-'+str(recording_id), False)
                evaluation_part = part_number
        
                update_or_create_evaluation(session, recording, evaluation_score, evaluation_problem, evaluation_part)
        
        return redirect('evaluate:evaluate', part_number=part_number)

def select_part(request):
    
    session_id = request.session.get('session_id')
    
    if not session_id:
        error_message = 'Please sign in.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:evaluation_login')}?{query_params}")
    
    session_obj = Session.objects.get(id=session_id)
    rater = session_obj.rater
    part1_raters = settings.EVAL_PART1_RATERS
    part2_raters = settings.EVAL_PART2_RATERS
    part3_raters = settings.EVAL_PART3_RATERS
    
    permissions=[
        rater.id in part1_raters,
        rater.id in part2_raters,
        rater.id in part3_raters
    ]
    
    parts_proportions = settings.PARTS_PROPORTIONS
    
    parts_completion_per_rater = Evaluation.objects.filter(
        session__rater=rater
    ).values('part').annotate(total=Count('id')).order_by('part')
    
    completion_dict = {
        item['part']: item['total'] for item in parts_completion_per_rater
    }
    
    completed_parts = [
        completion_dict.get(1, 0) == parts_proportions[0],
        completion_dict.get(2, 0) == parts_proportions[1],
        completion_dict.get(3, 0) == parts_proportions[2]
    ]
    
    success_message = request.GET.get('success', '')
    error_message = request.GET.get('error', '')
    
    context = {
        'permissions': zip(permissions, completed_parts),
        'success': success_message, 
        'error': error_message
    }
    
    return render(request, 'evaluate/select_part.html', context)