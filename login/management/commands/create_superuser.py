from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import os 

class Command(BaseCommand):
    help = 'Creates a superuser if one does not already exist, using environment variables for credentials.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not email or not password:
            self.stdout.write(self.style.ERROR(
                'Missing one or more required environment variables for superuser creation: '
                'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD'
            ))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" already exists. Skipping creation.'))
        else:
            self.stdout.write(f'Attempting to create superuser "{username}"...')
            try:
                User.objects.create_superuser(username=username, email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully.'))
            except Exception as e:
                raise CommandError(f"Failed to create superuser '{username}': {e}")