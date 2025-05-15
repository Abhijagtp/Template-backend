from django.core.management.base import BaseCommand
from templates.models import Category

class Command(BaseCommand):
    def handle(self, *args, **options):
        categories = ['React', 'HTML']
        for name in categories:
            Category.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS('Successfully seeded categories'))