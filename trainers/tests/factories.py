import factory
import random
from django.utils.text import slugify
from faker import Faker

from trainers.models import TrainerProfile
from accounts.tests.factories import UserFactory

fake = Faker('pl_PL')

class TrainerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrainerProfile

    user = factory.SubFactory(UserFactory)
    full_name = factory.LazyAttribute(lambda _: fake.name())
    
    @factory.lazy_attribute
    def username(self):
        return slugify(self.full_name) + '-' + str(random.randint(1000, 9999))
        
    sport = factory.LazyAttribute(lambda _: random.choice([
        'Trening personalny', 'Joga, Pilates', 'Boks', 'Pływanie', 
        'Trening siłowy, Crossfit', 'Zumba, Taniec', 'Bieganie', 
        'Sztuki walki', 'Kulturystyka'
    ]))
    location = factory.LazyAttribute(lambda _: fake.city())
    headline = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4)[:-1])
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    classes_description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=300))
    hourly_rate = factory.LazyAttribute(lambda _: round(random.uniform(50.0, 250.0), 2))
    contact_email = factory.LazyAttribute(lambda obj: obj.user.email)
    contact_phone = factory.LazyAttribute(lambda _: fake.phone_number()[:15])
