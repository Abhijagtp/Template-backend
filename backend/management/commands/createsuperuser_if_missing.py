from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Creates a superuser if it does not already exist'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='abhi').exists():
            User.objects.create_superuser(
                username='abhi',
                email='ajagtap2210@gmail.com',
                password='abhi@112'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully.'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists.'))