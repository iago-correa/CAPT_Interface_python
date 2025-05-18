from django.db import models

class Experiment(models.Model):
    session = models.ForeignKey(
        "login.Session", 
        on_delete=models.DO_NOTHING, 
        related_name="experiments")
    control = models.BooleanField(default=True) 

class Recording(models.Model):
    original_audio = models.ForeignKey(
        "practice.Audio", 
        on_delete=models.DO_NOTHING, 
        related_name="recordings")
    experiment= models.ForeignKey(
        Experiment, 
        on_delete=models.DO_NOTHING, 
        related_name="recordings")
    filename = models.CharField(max_length=255, unique=True)