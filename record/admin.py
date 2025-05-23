from django.contrib import admin
from .models import Recording

class RecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'recorded_audio', 'original_audio') 

admin.site.register(Recording, RecordingAdmin)