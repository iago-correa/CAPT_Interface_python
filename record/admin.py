from django.contrib import admin
from .models import Experiment, Recording

admin.site.register(Experiment)
admin.site.register(Recording)