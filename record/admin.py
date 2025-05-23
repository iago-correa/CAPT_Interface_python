from django.contrib import admin
from .models import Recording

admin.site.register(Recording)

class RecordingAdmin(admin.ModelAdmin):
    list_display = ('id', 'recorded_audio', 'original_audio') 