import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from login.models import Student, Rater

class Command(BaseCommand):
    help = 'Create test users: 01010101 and 02020202.'
    def handle(self, *args, **kwargs):

        rater_id = os.environ.get('TEST_RATER_ID')
        rater_password = os.environ.get('TEST_RATER_PASSWORD')

        try:
            Student.objects.get_or_create(
                student_id='01010101',
                control_group=True
            )
            Student.objects.get_or_create(
                student_id='02020202',
                control_group=False
            )
            Rater.objects.get_or_create(
                rater_id=rater_id,
                password=rater_password
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred during test users creation: {e}"))
