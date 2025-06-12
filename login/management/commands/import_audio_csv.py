from django.core.management.base import BaseCommand
from django.conf import settings
from practice.models import Audio
import csv
import os

class Command(BaseCommand):
    help = 'Import audios from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('type', type=str)

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_file']
        file_path = os.path.join(settings.STATIC_URL, csv_path)
        audio_type = kwargs['type']
        source_path = 'audio'

        self.stdout.write(f"Importing audios from: {file_path} with type: {audio_type}")

        try:
            with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)

                if 'filename' not in reader.fieldnames or 'transcript' not in reader.fieldnames:
                    self.stderr.write(self.style.ERROR("CSV must contain 'filename' and 'transcript' columns."))
                    return

                audios_created_count = 0
                audios_skipped_count = 0

                for row in reader:
                    filename = row['filename']
                    if not filename:
                        self.stdout.write(self.style.WARNING(f"Skipping row due to empty 'filename': {row}"))
                        continue

                    relative_file_path = os.path.join(source_path, filename)

                    # ✅ Check for existing entry
                    if Audio.objects.filter(file=relative_file_path, type=audio_type).exists():
                        audios_skipped_count += 1
                        continue

                    audio = Audio()
                    audio.transcript = row['transcript']
                    audio.type = audio_type
                    audio.file = relative_file_path
                    
                    audio.save()
                    audios_created_count += 1

            self.stdout.write(self.style.SUCCESS(f'{audios_created_count} audio entries imported successfully.'))
            self.stdout.write(self.style.WARNING(f'{audios_skipped_count} duplicate entries skipped.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"CSV file not found: {file_path}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
