from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils import timezone
from django.conf import settings

from .models import Student, Session, StudentCompletionReport, StudentDataExplorer
from practice.models import Activity, Audio

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
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_START'))),
            'end_time': timezone.make_aware(datetime.datetime(2025, 6, 19, 23, 59, 59)),
            'activity_type': 'train_record',
            'count_types': ['train_nat', 'train_gs'] # Count these types separately
        },
        {
            'name': '3. Training Session 2',
            'start_time': timezone.make_aware(datetime.datetime(2025, 6, 20, 8, 0, 0)),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('TRAINING_END'))),
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

total_audio_counts = {
    item['type']: item['count']
    for item in Audio.objects.values('type').annotate(count=Count('id'))
}

@admin.register(StudentDataExplorer)
class StudentDataExplorerAdmin(admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):
        # Get all students for the first dropdown
        all_students = Student.objects.order_by('student_id')
        
        # Get selections from the URL's query parameters
        student_id = request.GET.get('student_id')
        period_index_str = request.GET.get('period_index')
        
        selected_student = None
        selected_period_data = None # This will now hold a single dictionary, not a list
        selected_period_index = None

        # Proceed only if a student ID was provided
        if student_id:
            try:
                selected_student = Student.objects.get(pk=student_id)
                
                # Now, check if a period index was also provided and is valid
                if period_index_str is not None and period_index_str.isdigit():
                    period_index = int(period_index_str)
                    
                    # Check if the index is within the bounds of our config list
                    if 0 <= period_index < len(PERIODS_CONFIG):
                        selected_period_index = period_index
                        period = PERIODS_CONFIG[period_index]

                        # --- Run queries for the SINGLE selected period ---
                        start = period['start_time'].replace(tzinfo=None)
                        end = period['end_time'].replace(tzinfo=None)
                        act_type = period['activity_type']
                        
                        sessions = Session.objects.filter(
                            student=selected_student, start_time__gte=start, end_time__lte=end
                        ).order_by('start_time')
                        
                        all_activities = Activity.objects.filter(
                            session__student=selected_student, time__range=(start, end)
                        ).order_by('time')
                        
                        filtered_activities = all_activities.filter(type=act_type)

                        completion_counts = {}
                        for audio_type in period['count_types']:
                            count = all_activities.filter(
                                recording__isnull=False, recording__original_audio__type=audio_type
                            ).aggregate(
                                unique_recordings=Count('recording__original_audio', distinct=True)
                            )['unique_recordings']
                            completion_counts[audio_type] = count if count is not None else 0
                        
                        # Store the results in a single dictionary
                        selected_period_data = {
                            'name': period['name'],
                            'sessions': sessions,
                            'all_activities': all_activities,
                            'filtered_activities': filtered_activities,
                            'activity_type': act_type,
                            'completion_counts': completion_counts,
                        }

            except Student.DoesNotExist:
                selected_student = None

        context = {
            **self.admin_site.each_context(request),
            'title': 'Student Data Explorer',
            'all_students': all_students,
            'periods': PERIODS_CONFIG, # Pass the config to populate the period dropdown
            'selected_student': selected_student,
            'selected_period_index': selected_period_index, # To re-select the dropdown on page load
            'results': selected_period_data, # Pass the single dictionary of results
        }
        
        return TemplateResponse(request, "admin/student_data_explorer.html", context)

@admin.register(StudentCompletionReport)
class StudentCompletionReportAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        report_data = []

        total_audio_counts = {
            item['type']: item['count']
            for item in Audio.objects.values('type').annotate(count=Count('id'))
        }

        for period in PERIODS_CONFIG:
            period_name = period['name']
            start_time = period['start_time'].replace(tzinfo=None)
            end_time = period['end_time'].replace(tzinfo=None)
            
            period_counts = {}
            for audio_type in period['count_types']:

                # 1. Get the actual number of audios in the DB. This is the default target.
                completion_target = total_audio_counts.get(audio_type, 0)
                display_total = completion_target

                # 2. Apply the special rule for 'train_gs'
                if audio_type == 'train_gs':
                    # The target for completion is now a fixed number.
                    completion_target = 20
                    # The number displayed in the report is also fixed.
                    display_total = 20

                num_students_completed = 0
                # We only run the query if there is a target to meet.
                if completion_target > 0:
                    num_students_completed = Activity.objects.filter(
                        time__range=(start_time, end_time),
                        recording__isnull=False,
                        recording__original_audio__type=audio_type
                    ).values(
                        'session__student'
                    ).annotate(
                        unique_recordings=Count('recording__original_audio', distinct=True)
                    ).filter(
                        unique_recordings__gte=completion_target
                    ).count()

                period_counts[audio_type] = {
                    'completed': num_students_completed,
                    'total_required': display_total,
                }
            
            report_data.append({
                'name': period_name,
                'counts': period_counts,
            })
            
        context = {
            **self.admin_site.each_context(request),
            'title': 'Student Completion Report',
            'report_data': report_data,
        }
        
        return TemplateResponse(request, "admin/completion_report.html", context)

class StudentCompletionFilter(admin.SimpleListFilter):
    title = 'Completion Status by Period'
    parameter_name = 'completion_status'

    def lookups(self, request, model_admin):
        """Dynamically generates a simpler list of filter options."""
        options = []
        # We now generate one "completed" and "not completed" link per period.
        for i, period in enumerate(PERIODS_CONFIG):
            options.append((f'{i}-completed', f"Completed: {period['name']}"))
            options.append((f'{i}-not_completed', f"Not Completed: {period['name']}"))
        return options

    def queryset(self, request, queryset):
        """Filters the Student list based on the new completion criteria."""
        value = self.value()
        if not value:
            return queryset

        try:
            # Parse the simpler value, e.g., "1-completed"
            period_index_str, status = value.split('-')
            period_index = int(period_index_str)
        except (ValueError, IndexError):
            return queryset

        if not (0 <= period_index < len(PERIODS_CONFIG)):
            return queryset

        period = PERIODS_CONFIG[period_index]
        start_time, end_time = period['start_time'], period['end_time']
        
        completed_student_ids = []

        # --- Conditional Logic Based on the Selected Period ---

        if period_index in [0, 3, 4]:  # Logic for Pre, Post, and Delayed periods
            audio_type = 'test_nat'
            completion_target = total_audio_counts.get(audio_type, 0)
            
            if completion_target > 0:
                # Find students who completed ALL unique 'test_nat' audios
                completed_student_ids = Activity.objects.filter(
                    time__range=(start_time, end_time),
                    recording__isnull=False,
                    recording__original_audio__type=audio_type
                ).values('session__student').annotate(
                    unique_recordings=Count('recording__original_audio', distinct=True)
                ).filter(
                    unique_recordings=completion_target
                ).values_list('session__student_id', flat=True)

        elif period_index in [1, 2]:  # New, complex logic for Training periods
            # We must find the two groups of completers separately and combine them.

            # A) Find completers from the Control Group (control_group=True)
            # They must complete all 'train_nat' audios.
            nat_target = total_audio_counts.get('train_nat', 0)
            control_completers = []
            if nat_target > 0:
                control_completers = list(Activity.objects.filter(
                    session__student__control_group=True,
                    time__range=(start_time, end_time),
                    recording__isnull=False,
                    recording__original_audio__type='train_nat'
                ).values('session__student').annotate(
                    c=Count('recording__original_audio', distinct=True)
                ).filter(c=nat_target).values_list('session__student_id', flat=True))

            # B) Find completers from the Experimental Group (control_group=False)
            # They must complete at least 20 unique 'train_gs' audios.
            gs_target = 20
            experimental_completers = list(Activity.objects.filter(
                session__student__control_group=False,
                time__range=(start_time, end_time),
                recording__isnull=False,
                recording__original_audio__type='train_gs'
            ).values('session__student').annotate(
                c=Count('recording__original_audio', distinct=True)
            ).filter(c__gte=gs_target).values_list('session__student_id', flat=True))
            
            # Combine the two lists of student IDs
            completed_student_ids = control_completers + experimental_completers

        # --- Apply the final filter to the student list ---
        if status == 'completed':
            return queryset.filter(pk__in=completed_student_ids)
        if status == 'not_completed':
            return queryset.exclude(pk__in=completed_student_ids)
            
        return queryset

class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_id', 'control_group')
    list_filter = ('control_group', StudentCompletionFilter)

admin.site.register(Student, StudentAdmin)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'start_time', 'end_time') 

admin.site.register(Session, SessionAdmin)