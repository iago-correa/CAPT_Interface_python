from django.contrib import admin
from .models import Activity, Audio

admin.site.register(Activity)

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'time', 'session', 'audio', 'recording') 

admin.site.register(Audio)

class AudioAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'type', 'student','transcript') 