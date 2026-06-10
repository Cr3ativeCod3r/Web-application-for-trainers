import factory
from faker import Faker
from apps.accounts.models import CustomUser, TrainerStatus

fake = Faker('pl_PL')

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    is_active = True
    status = TrainerStatus.PENDING_APPLICATION
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password('testpassword123')
