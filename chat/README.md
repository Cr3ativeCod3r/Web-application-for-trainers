# Chat service

FastAPI microservice for real-time conversations between clients and trainers.
It owns its PostgreSQL database and never connects to the main app's one.

## Interfaces

| Direction | What |
|---|---|
| in: HTTP | `POST /rooms`, `GET /rooms`, `GET /rooms/{id}/messages`, `POST /ws-tickets` (Bearer token) |
| in: WebSocket | `/ws/chat/{room_id}?ticket=...` |
| in: Redis Stream | `coachly.users.v1` (consumer group `chat-service`) → `chat_users` |
| Redis Pub/Sub | `chat_messages` (fan-out between instances), `chat_control` (close a user's sockets) |
| ops | `GET /health` (liveness), `GET /ready` (database + Redis) |

## Configuration

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` of the chat database |
| `REDIS_URL` | Redis used for streams, Pub/Sub, tickets and rate limits |
| `JWT_PUBLIC_KEY` / `JWT_PUBLIC_KEY_FILE` | public half of the main app's ES256 key |
| `CHAT_CORS_ORIGINS` | comma-separated origins of the main app |

## Development

```bash
alembic upgrade head
uvicorn main:app --reload --port 8001
CHAT_TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/chat_test uv run pytest
```
