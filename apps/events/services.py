import json
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .bus import get_bus
from .models import OutboxEvent

logger = logging.getLogger(__name__)


def record_event(*, stream: str, event_type: str, aggregate_id, payload: dict) -> OutboxEvent:
    """
    Store an event in the outbox as part of the caller's transaction and ask the
    relay to publish it once that transaction commits.
    """
    event = OutboxEvent.objects.create(
        stream=stream,
        event_type=event_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
    )
    transaction.on_commit(_schedule_relay)
    return event


def _schedule_relay():
    from .tasks import relay_outbox_events

    try:
        relay_outbox_events.delay()
    except Exception:
        # The broker being down must not fail the user's request: the event is
        # safely stored and the periodic relay will pick it up.
        logger.warning("Could not schedule the outbox relay", exc_info=True)


def relay_pending_events(batch_size: int = 100) -> int:
    """
    Publish unpublished outbox events in id order. Returns the number published.

    Rows are claimed with SKIP LOCKED, so several workers can relay in parallel
    without publishing the same event twice in the normal case. If publishing
    fails half-way, the transaction rolls back and the batch is retried later:
    delivery is at-least-once, and consumers deduplicate by event id.
    """
    published = 0
    bus = get_bus()
    while True:
        with transaction.atomic():
            events = list(
                OutboxEvent.objects.filter(published_at__isnull=True)
                .order_by('id')
                .select_for_update(skip_locked=True)[:batch_size]
            )
            if not events:
                return published

            pipe = bus.pipeline(transaction=False)
            for event in events:
                pipe.xadd(
                    event.stream,
                    {
                        'id': event.pk,
                        'type': event.event_type,
                        'aggregate_id': event.aggregate_id,
                        'occurred_at': event.created_at.isoformat(),
                        'payload': json.dumps(event.payload),
                    },
                    maxlen=settings.EVENT_STREAM_MAXLEN,
                    approximate=True,
                )
            pipe.execute()

            OutboxEvent.objects.filter(pk__in=[e.pk for e in events]).update(published_at=timezone.now())
            published += len(events)


def purge_published_events(older_than_days: int = 7) -> int:
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = OutboxEvent.objects.filter(published_at__lt=cutoff).delete()
    return deleted
