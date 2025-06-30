from django.contrib import admin
from .models import Evaluation

class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recording__recorded_audio', 'score', 'problem') 

admin.site.register(Evaluation, EvaluationAdmin)