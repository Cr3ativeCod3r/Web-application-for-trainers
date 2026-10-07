from django.db import models


class OutboxEvent(models.Model):
    """
    Transactional outbox: an event is written in the same database transaction as
    the change it describes, and a separate relay publishes it to the message bus.

    This avoids the dual-write problem - publishing straight to Redis from a view
    either loses the event (crash after COMMIT) or announces a change that was
    rolled back (crash before COMMIT). The primary key doubles as a monotonically
    increasing version that consumers use to discard stale or duplicated events.
    """

    stream = models.CharField(max_length=100)
    event_type = models.CharField(max_length=100)
    aggregate_id = models.CharField(max_length=64)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # The relay only ever scans unpublished rows; keep that index tiny.
            models.Index(
                fields=['id'],
                name='outbox_unpublished_idx',
                condition=models.Q(published_at__isnull=True),
            ),
        ]

    def __str__(self):
        return f"#{self.pk} {self.event_type} ({self.aggregate_id})"
