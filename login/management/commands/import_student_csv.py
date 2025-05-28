import csv
from django.core.management.base import BaseCommand
from login.models import Student

class Command(BaseCommand):
    help = 'Import data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file']
        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                Student.objects.create(
                    student_id=row['student_id'],
                    control_group=row['control_group']
                )
        self.stdout.write(self.style.SUCCESS('Data imported successfully.'))
