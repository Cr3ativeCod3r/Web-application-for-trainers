import pytest
from apps.trainers.tests.factories import TrainerProfileFactory, TrainerPostFactory
from apps.trainers.models import TrainerPost

@pytest.mark.django_db
class TestTrainerProfileModel:

    def test_string_representation(self):
        """Test the __str__ representation of TrainerProfile."""
        profile = TrainerProfileFactory.build(full_name="Jan Kowalski")
        assert str(profile) == f"Jan Kowalski ({profile.user.email})"


@pytest.mark.django_db
class TestTrainerPostModel:
    def test_slug_generation_on_save(self):
        """Test that a slug is generated automatically based on the title."""
        post = TrainerPostFactory(title="Nowy trening dla kazdego")
        assert post.slug == "nowy-trening-dla-kazdego"

    def test_slug_uniqueness_counter(self):
        """Test that duplicate titles get unique slugs with numeric suffixes."""
        trainer = TrainerProfileFactory()
        post1 = TrainerPostFactory(trainer=trainer, title="Unikalny tytul")
        post2 = TrainerPostFactory(trainer=trainer, title="Unikalny tytul")
        post3 = TrainerPostFactory(trainer=trainer, title="Unikalny tytul")

        assert post1.slug == "unikalny-tytul"
        assert post2.slug == "unikalny-tytul-1"
        assert post3.slug == "unikalny-tytul-2"

    def test_string_representation(self):
        """Test the __str__ representation of TrainerPost."""
        post = TrainerPostFactory(title="Porady trenera")
        assert str(post) == f"Porady trenera - {post.trainer.full_name}"
