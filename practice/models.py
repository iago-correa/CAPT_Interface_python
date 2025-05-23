from django.db import models
from record.models import Recording
from login.models import Student

class Audio(models.Model):
    
    TYPE_CHOICES = [
        ('test_nat', 'Pre-training native reference'),
        ('train_nat', 'Native speaker recording'),
        ('train_gs', 'Synthesized golden speaker')
    ]
    
    file = models.FileField(upload_to='audio/')
    transcript = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, blank=False, default='train_gs')
    student = models.ForeignKey( # In case it is a synthesized speech, this indicates the original student
        Student, 
        blank=True, 
        null=True, 
        on_delete=models.DO_NOTHING, 
        related_name='audios_for_practice')
    
    def __str__(self):
        return f"{self.file.url}: {self.transcript}"

class Activity(models.Model):
    
    TYPE_CHOICES = [
        ('train_listen_ref', 'Listening to reference during training'),
        ('train_listen_own', 'Listening to own recording during training'),
        ('train_record', 'Training recording'),
        ('test_pre_record', 'Pre-training recording'),
        ('test_post_record', 'Post-training recording'),
        ('test_delay_record', 'Delayed post-training recording')
    ]
    
    session = models.ForeignKey("login.Session", 
                                blank=False,
                                on_delete=models.CASCADE, 
                                related_name="activities")
    audio = models.ForeignKey(Audio, 
                              blank=True,
                              null=True,
                              on_delete=models.CASCADE, 
                              related_name="activities")
    recording = models.ForeignKey(Recording, 
                              blank=True,
                              null=True,
                              on_delete=models.CASCADE, 
                              related_name="activities")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=False)
    time = models.DateTimeField(auto_now_add=True, blank=False)
    
    def __str__(self):
        return f"{self.type}: {self.time}"

    class Meta:
        verbose_name_plural = "Activities"