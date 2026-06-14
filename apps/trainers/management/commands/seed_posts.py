from django.core.management.base import BaseCommand
from apps.trainers.models import TrainerProfile, TrainerPost
from apps.accounts.models import TrainerStatus
import random
from datetime import timedelta
from django.utils import timezone

try:
    from faker import Faker
except ImportError:
    Faker = None

class Command(BaseCommand):
    help = 'Generuje po 5 postów dla każdego aktywnego trenera'

    def handle(self, *args, **kwargs):
        if not Faker:
            self.stdout.write(self.style.ERROR("Faker is not installed. Run 'uv add faker'"))
            return

        fake = Faker('pl_PL')
        trainers = TrainerProfile.objects.filter(user__status=TrainerStatus.APPROVED_TRAINER)
        count = 0
        
        for trainer in trainers:
            for _ in range(5):
                title = fake.sentence(nb_words=6).replace('.', '')
                
                # Generate 3 random paragraphs
                paragraphs = [fake.paragraph(nb_sentences=4) for _ in range(3)]
                
                content = f"<h2>{fake.sentence(nb_words=4).replace('.', '')}</h2>"
                content += f"<p>{paragraphs[0]}</p>"
                content += f"<h3>{fake.sentence(nb_words=3).replace('.', '')}</h3>"
                content += f"<p>{paragraphs[1]}</p>"
                content += f"<ul><li>{fake.sentence(nb_words=3)}</li><li>{fake.sentence(nb_words=4)}</li><li>{fake.sentence(nb_words=3)}</li></ul>"
                content += f"<p>{paragraphs[2]}</p>"
                
                post = TrainerPost(
                    trainer=trainer,
                    title=title,
                    content=content,
                )
                post.image.name = 'post_images/post_hero.png'
                post.save()
                
                # Randomize the created_at date within the last 30 days
                post.created_at = timezone.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                post.save(update_fields=['created_at'])
                
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Pomyślnie wygenerowano {count} postów dla {trainers.count()} trenerów.'))
