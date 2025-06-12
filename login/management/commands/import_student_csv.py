import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from login.models import Student
import requests
import io

class Command(BaseCommand):
    help = 'Import students from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_file']
        file_path = os.path.join(settings.STATIC_URL, csv_path)

        #with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
        response = requests.get(file_path)
        response.raise_for_status()  # Optional: raises error on bad HTTP status
        csvfile = io.StringIO(response.content.decode('utf-8-sig'))
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            Student.objects.get_or_create(
                student_id=row['student_id'],
                control_group=row['control_group']
            )
    
        self.stdout.write(self.style.SUCCESS('Data imported successfully.'))
