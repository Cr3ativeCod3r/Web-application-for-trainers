from celery import shared_task

from . import services


@shared_task(ignore_result=True)
def relay_outbox_events():
    services.relay_pending_events()


@shared_task(ignore_result=True)
def purge_published_outbox_events():
    services.purge_published_events()
