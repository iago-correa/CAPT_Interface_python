from django.db import models

class Recording(models.Model):
    original_audio = models.ForeignKey(
        "practice.Audio", 
        on_delete=models.DO_NOTHING, 
        related_name="recordings")
    recorded_audio = models.FileField(upload_to='recording/')