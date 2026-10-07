from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.integration_events import publish_user_updated


class Command(BaseCommand):
    help = (
        "Queue a user.updated event for every user. Used to bootstrap a new consumer "
        "(e.g. a fresh chat database) or to repair one that drifted. Safe to re-run: "
        "consumers apply only events newer than what they already have."
    )

    def handle(self, *args, **options):
        user_ids = get_user_model().objects.order_by('pk').values_list('pk', flat=True)
        count = 0
        for user_id in user_ids.iterator():
            publish_user_updated(user_id)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Queued {count} user snapshots."))
