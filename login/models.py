from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=10, unique=True)
    control_group = models.BooleanField(default=True)

    def __str__(self):
        return self.student_id

class Session(models.Model):
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(auto_now=True)

    student = models.ForeignKey(
        Student, 
        blank=False, 
        null=False, 
        on_delete=models.CASCADE, 
        related_name='sessions')
    
    def __str__(self):
        return f"Session {self.id} for {self.student.student_id} from {self.start_time} to {self.end_time}"