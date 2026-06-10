from django.core.management.base import BaseCommand
from trainers.tests.factories import TrainerProfileFactory

class Command(BaseCommand):
    help = 'Tworzy fałszywych użytkowników ze statusem PENDING_APPLICATION za pomocą factory_boy'

    def handle(self, *args, **kwargs):
        self.stdout.write('Rozpoczynam generowanie 20 oczekujących trenerów...')
        
        created_count = 0
        for _ in range(20):
            try:
                TrainerProfileFactory()
                created_count += 1
            except Exception as e:
                self.stderr.write(f'Błąd podczas tworzenia trenera: {e}')
                
        self.stdout.write(self.style.SUCCESS(f'Pomyślnie utworzono {created_count} oczekujących trenerów.'))
