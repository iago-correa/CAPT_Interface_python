from django.core.management.base import BaseCommand
from django.conf import settings
from practice.models import Audio
from login.models import Student
from django.conf import settings
import glob
import csv
import os

class Command(BaseCommand):
    help = 'Import audios from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_file']
        file_path = os.path.join(settings.BASE_DIR, csv_path)

        experiment_students = Student.objects.filter(control_group=False)
        self.stdout.write(f"Importing audios from: {file_path} with type: train_gs")

        try:
            
            gs_path = 'gs'
            for student in experiment_students:
            #glob.glob(f'.{settings.STATIC_URL}{gs_path}/*'):

                speaker_id = student.id
                print(speaker_id)

                with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                    reader = csv.DictReader(csvfile)
                
                    audios_created_count = 0
                    for row in reader:
                        filename = row['filename'].replace('.mp3', '.wav')
                        if not filename:
                            self.stdout.write(self.style.WARNING(f"Skipping row due to empty 'filename': {row}"))
                            continue
                        
                        audio_filename = os.path.join('gs', speaker_id, filename)
                        
                        if os.path.exists(os.path.join({settings.STATIC_URL}, audio_filename)):
                            audio = Audio()
                            audio.transcript = row['transcript']
                            audio.type = 'train_gs'
                            audio.student = Student.objects.get(id = speaker_id)
                            audio.file = audio_filename

                            audio.save()
                            audios_created_count += 1

                self.stdout.write(self.style.SUCCESS(f'{audios_created_count} audio entries imported successfully.')) 

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"CSV file not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))