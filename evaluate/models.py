from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
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

    def clean(self):
        if self.recording and self.session and self.session.rater:
            # Check if an evaluation already exists for this recording and rater
            # Exclude the current instance if it's an update
            qs = Evaluation.objects.filter(
                recording=self.recording,
                session__rater=self.session.rater
            )

            if self.pk: # If updating an existing instance
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError(
                    "This rater has already evaluated this recording.",
                    code='duplicate_evaluation'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"{self.recording.recorded_audio}: {self.score}"