from django.contrib import admin
from .models import Student, Session

class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_id', 'control_group') 

admin.site.register(Student, StudentAdmin)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'start_time', 'end_time') 

admin.site.register(Session, SessionAdmin)