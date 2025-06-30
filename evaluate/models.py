from django.db import models
from record.models import Recording

class Evaluation(models.Model):
    
    SCORE_CHOICES = [
        (1, 'Bad'),
        (2, 'Poor'),
        (3, 'Fair'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]
    
    session = models.ForeignKey("login.Session", 
                                blank=False,
                                on_delete=models.CASCADE, 
                                related_name="evaluations")
    recording = models.ForeignKey(Recording, 
                              blank=True,
                              null=True,
                              on_delete=models.CASCADE, 
                              related_name="evaluations")
    score = models.IntegerField(choices=SCORE_CHOICES, default=1)
    problem = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.recording.recorded_audio}: {self.score}"