from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from record.models import Recording

class Evaluation(models.Model):
    
    SCORE_CHOICES = [0,1,2,3,4,5,6,7,8,9]
    
    session = models.ForeignKey("login.Session", 
                                blank=False,
                                on_delete=models.CASCADE, 
                                related_name="evaluations")
    recording = models.ForeignKey(Recording, 
                              blank=True,
                              null=True,
                              on_delete=models.CASCADE, 
                              related_name="evaluations")
    score = models.IntegerField(default=-1, validators=[MinValueValidator(0), MaxValueValidator(9)])
    problem = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.recording.recorded_audio}: {self.score}"