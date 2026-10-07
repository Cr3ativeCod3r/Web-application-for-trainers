"""
Event contracts published by this service. Other services depend on these names
and payload shapes, so changes must stay backwards compatible (add fields, never
rename or remove them); a breaking change gets a new stream version.
"""

USER_EVENTS_STREAM = 'coachly.users.v1'

USER_UPDATED = 'user.updated'
USER_DELETED = 'user.deleted'
