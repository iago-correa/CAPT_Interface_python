from django.db import models

class Audio(models.Model):
    filename = models.CharField(max_length=255, unique=True)
    transcript = models.TextField()

    def __str__(self):
        return f"{self.filename}: {self.transcript}"

class Activity(models.Model):
    session = models.ForeignKey("login.Session", on_delete=models.CASCADE, related_name="activities")
    audio = models.ForeignKey(Audio, on_delete=models.CASCADE, related_name="activities")