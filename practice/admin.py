from django.contrib import admin
from .models import Activity, Audio

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'time', 'session', 'audio', 'recording') 

admin.site.register(Activity, ActivityAdmin)

class AudioAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'type', 'student','transcript') 

admin.site.register(Audio, AudioAdmin)