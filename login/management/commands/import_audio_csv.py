from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from practice.models import Audio
import csv
import os

class Command(BaseCommand):
    help = 'Import audios from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('source_path', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file']
        audio_type = kwargs['type']
        source_path = kwargs['source_path']
        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                with open(os.path.join(source_path, row['filename']), 'rb') as audio_file:
                    
                    audio = Audio()
                    audio.transcript = row['transcript']
                    audio.type = audio_type
                    
                    audio_file = File(audio_file, name=row['filename'])
                    audio.file.save(row['filename'], audio_file, save=True)

        self.stdout.write(self.style.SUCCESS('Data imported successfully.'))