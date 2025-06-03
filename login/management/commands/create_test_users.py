import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from login.models import Student
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create test users: 01010101 and 02020202'

    def handle(self, *args, **kwargs):

        try:
            Student.objects.get_or_create(
                student_id='01010101',
                control_group=True
            )
            Student.objects.get_or_create(
                student_id='02020202',
                control_group=False
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred during test users creation: {e}"))
