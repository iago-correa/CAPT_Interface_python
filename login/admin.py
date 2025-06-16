from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from django.utils import timezone
from django.conf import settings

from .models import Student, Session, StudentCompletionReport, StudentDataExplorer
from practice.models import Activity, Audio

import datetime

class StudentCompletionFilter(admin.SimpleListFilter):
    title = 'Completion Status'  # Title for the filter sidebar
    parameter_name = 'completion_status'  # URL parameter

    def lookups(self, request, model_admin):

        return (
            ('completed', 'Completed all test recordings'),
            ('not_completed', 'Not completed all test recordings'),
        )

    def queryset(self, request, queryset):
        
        # --- Re-run the query to find the IDs of completed students ---
        required_audio_count = Audio.objects.filter(type='test_nat').count()
        activity_conditions = Q(
            type='test_pre_record',
            recording__original_audio__type='test_nat',
            recording__isnull=False
        )
        
        completed_student_ids = Activity.objects.filter(activity_conditions)\
            .values('session__student')\
            .annotate(distinct_audio_count=Count('recording__original_audio', distinct=True))\
            .filter(distinct_audio_count=required_audio_count)\
            .values_list('session__student_id', flat=True)
        # --- End of query logic ---

        if self.value() == 'completed':
            # If the user clicks 'Completed', filter the list to these IDs
            return queryset.filter(pk__in=completed_student_ids)

        if self.value() == 'not_completed':
            # If the user clicks 'Not Completed', exclude these IDs
            return queryset.exclude(pk__in=completed_student_ids)
        
        return queryset

class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_id', 'control_group')
    list_filter = ('control_group', StudentCompletionFilter)

admin.site.register(Student, StudentAdmin)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'start_time', 'end_time') 

admin.site.register(Session, SessionAdmin)
    
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
            'count_types': ['train_nat', 'train_gs'] # Count these types separately
        },
        {
            'name': '5. Delayed Recording',
            'start_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('DELAY_START'))),
            'end_time': timezone.make_aware(datetime.datetime(*period_dates_config.get('DELAY_END'))),
            'activity_type': 'test_delay_record',
            'count_types': ['train_nat', 'train_gs'] # Count these types separately
        }
    ]
except (AttributeError, TypeError):
    # Fallback if settings.PERIOD_DATES is not configured, prevents crashing
    PERIODS_CONFIG = []

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
                        start = period['start_time']
                        end = period['end_time']
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
        # This list will hold the final data for our report
        report_data = []

        # To be efficient, let's get the total count of audios per type once
        total_audio_counts = {
            item['type']: item['count']
            for item in Audio.objects.values('type').annotate(count=Count('id'))
        }

        # Loop through each defined period from our shared config
        for period in PERIODS_CONFIG:
            period_name = period['name']
            start_time = period['start_time']
            end_time = period['end_time']
            
            # This dictionary will store results for the current period
            period_counts = {}

            # For each period, loop through the audio types we need to report on
            for audio_type in period['count_types']:
                # Get the total number of audios for this type from our cache
                total_required = total_audio_counts.get(audio_type, 0)
                
                num_students_completed = 0
                if total_required > 0:
                    # This is our main query. It finds students who have a distinct
                    # recording count that matches the total required count for that type.
                    num_students_completed = Activity.objects.filter(
                        time__range=(start_time, end_time),
                        recording__isnull=False,
                        recording__original_audio__type=audio_type
                    ).values(
                        'session__student' # Group by student
                    ).annotate(
                        unique_recordings=Count('recording__original_audio', distinct=True)
                    ).filter(
                        unique_recordings=total_required
                    ).count() # Finally, count how many students met the criteria
                
                # Store the result for this audio type
                period_counts[audio_type] = {
                    'completed': num_students_completed,
                    'total_required': total_required,
                }
            
            # Add this period's full report to our main data list
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
