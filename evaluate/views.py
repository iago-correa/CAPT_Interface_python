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

def get_students_to_evaluate(target_period=4):
    
    report_data = []

    ignored_ids = settings.IGNORED_STUDENTS

    previous_control_ids = set()
    previous_experimental_ids = set()
    previous_total_ids = set()

    for i, period in enumerate(PERIODS_CONFIG):
        period_name = period['name']
        start_time = period['start_time'].replace(tzinfo=None)
        end_time = period['end_time'].replace(tzinfo=None)
        audio_type = period['count_types']
        completion_target = 20

        # Fetch current period completions
        completions_qs = Activity.objects.filter(
            time__range=(start_time, end_time),
            recording__isnull=False,
            recording__original_audio__type__in=audio_type
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

        control_ids = set()
        experimental_ids = set()

        for entry in completions_qs:
            student_id = entry['session__student']
            if entry['session__student__control_group']:
                control_ids.add(student_id)
            else:
                experimental_ids.add(student_id)

        total_ids = control_ids | experimental_ids

        period_counts = {
            'control_completed': len(control_ids),
            'control_total': control_total,
            'experimental_completed': len(experimental_ids),
            'experimental_total': experimental_total,
            'total_completed': len(total_ids),
            'total_total': control_total + experimental_total,
        }

        if i == 0:
            retained_control = control_ids
            retained_experimental = experimental_ids
            retained_total = total_ids
        else:
            retained_control = control_ids & previous_control_ids
            retained_experimental = experimental_ids & previous_experimental_ids
            retained_total = total_ids & previous_total_ids

        retention_counts = {
            'control_completed': len(retained_control),
            'control_total': len(previous_control_ids),
            'experimental_completed': len(retained_experimental),
            'experimental_total': len(previous_experimental_ids),
            'total_completed': len(retained_total),
            'total_total': len(previous_total_ids),
        }

        previous_control_ids = retained_control
        previous_experimental_ids = retained_experimental
        previous_total_ids = retained_total

        report_data.append({
            'name': period_name,
            'counts': period_counts,
            'retention': retention_counts,
        })

    context = {
        **self.admin_site.each_context(request),
        'title': 'Student Completion Report',
        'report_data': report_data,
    }

    return context

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
        
        # students_to_evaluate = get_students_to_evaluate()
        students_to_evaluate = Student.objects.exclude(
            id__in=settings.IGNORED_STUDENTS
        )
        
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
        
        completion = int(100*num_completed/num_total)
        
        return render(request, 'evaluate/evaluate.html', {
            'scores': range(10),
            'num_completed': num_completed,
            'num_total': num_total,
            'completion': completion,
            'evaluation_set': evaluation_set, 
            'csrf_token_value': request.META.get('CSRF_COOKIE')
        })
    
    elif request.method == "POST":
        
        session = Session.objects.get(id = request.session['session_id'])
        
        for key in request.POST:
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
    