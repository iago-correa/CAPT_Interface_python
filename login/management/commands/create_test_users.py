import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from login.models import Student
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create admin and test users: 01010101 and 02020202'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['username']

        try:
            if not User.objects.filter(is_superuser=True).first():
                user = User.objects.create(
                    username = username,
                    is_superuser = True
                )
                user.set_password(password)
                user.save()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred on super user creation: {e}"))

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
