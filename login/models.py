from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=10, unique=True)
    control_group = models.BooleanField(default=True)

    def __str__(self):
        return self.student_id

class Rater(models.Model):
    rater_id = models.CharField(max_length=10, unique=True)
    password = models.CharField(max_length=20)

    def __str__(self):
        return self.rater_id

class Session(models.Model):
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(auto_now=True)

    student = models.ForeignKey(
        Student, 
        blank = True, 
        null = True, 
        on_delete = models.CASCADE, 
        related_name = 'sessions'
    )
    
    rater = models.ForeignKey(
        Rater,
        blank = True,
        null = True,
        on_delete = models.CASCADE,
        related_name = 'sessions'
    )
    
    def __str__(self):
        return f"{self.student.student_id}: {self.start_time} - {self.end_time}"
    
class StudentCompletionReport(Student):
    class Meta:
        # No new DB table will be created.
        proxy = True
        
        verbose_name = 'Completion Report'
        verbose_name_plural = 'Completion Reports'

class StudentDataExplorer(Student):
    class Meta:
        proxy = True
        verbose_name = 'Student Data Explorer'
        verbose_name_plural = 'Student Data Explorer'