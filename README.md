# Coachly

A marketplace for sports trainers: clients search for trainers by sport, location and training type, chat with them in real time, read their articles, and can take an AI quiz that suggests a sport. Trainers apply, get moderated by an admin, and manage their profile and publications.

<img width="1080" height="1920" alt="Home page" src="https://github.com/user-attachments/assets/591990cb-0010-4334-a7e1-a5628a589892" />

**Stack:** Django 6 · PostgreSQL 15 · Celery + Redis · FastAPI (WebSockets) · SQLAlchemy 2 (async) + Alembic · Google Gemini API · Cloudflare R2 · Docker Compose · uv · pytest · GitHub Actions

## Features

- **Trainer search**: filter by sport, location and online/stationary, with autocomplete.
- **Moderated trainer profiles**: a trainer applies, an admin approves; later edits are stored as a *pending update* and only go live after approval (with a preview of the result).
- **Real-time chat** between clients and trainers (separate FastAPI service, see below).
- **Knowledge base**: trainers publish articles with a rich-text editor.
- **AI sport matcher**: a 13-question quiz; Gemini picks a sport from the ones actually offered by trainers on the platform and links matching trainers.

  <img width="389" height="642" alt="AI quiz" src="https://github.com/user-attachments/assets/f0d976ef-19ec-42b4-9bd1-56f4e23e6a96" />
- **Auth**: e-mail + password with activation link, password reset, Google OAuth (django-allauth).
- **Custom admin dashboard** for moderation (approve/reject, ban, preview, delete posts).

<img width="1920" height="1080" alt="Trainer profile" src="https://github.com/user-attachments/assets/10452c21-30e9-4de1-a677-8650abfe89ab" />

## Architecture

```text
                    ┌──────────────┐  HTTP   ┌──────────────────────┐
 Browser ──────────▶│ Django (web) │────────▶│ PostgreSQL           │
   │                │  gunicorn    │         │  Django tables       │
   │                └──────┬───────┘         │  chat_rooms/messages │
   │                       │ .delay()        └──────────▲───────────┘
   │                       ▼                            │ asyncpg
   │                ┌──────────────┐  Redis  ┌──────────┴───────────┐
   │                │ Celery worker│◀───────▶│ Redis                │
   │                └──────────────┘         │  broker, cache,      │
   │  WebSocket + JWT                        │  chat Pub/Sub        │
   └────────────────────────────────────────▶│                      │
                    ┌──────────────┐         └──────────▲───────────┘
                    │ chat (FastAPI│────────────────────┘
                    │  + uvicorn)  │
                    └──────────────┘
```

| Container | Responsibility |
|---|---|
| `web` | Django app: pages, forms, admin dashboard, JWT issuing |
| `db` | PostgreSQL shared by both services |
| `redis` | Celery broker, rate-limit cache, chat Pub/Sub |
| `celery_worker` | Sends e-mails outside the request cycle |
| `chat` | FastAPI service handling WebSockets and chat history |

<img width="6330" height="5054" alt="Architecture diagram" src="https://github.com/user-attachments/assets/ac177999-e970-4a07-9fb6-cf1cd40630a9" />

### Code layout

```text
apps/
├── accounts/         # users, registration/activation, login, chat page + user-info API
├── trainers/         # profiles, moderation flow, search, posts
├── pages/            # static pages, knowledge base, AI quiz
└── admin_dashboard/  # moderation UI
core/                 # settings, URLs, middleware, HTML sanitizer
chat/                 # FastAPI microservice (own models, Alembic migrations, tests)
```

Inside an app, **`services.py`** holds operations that change state (wrapped in transactions), **`selectors.py`** holds read queries, and views stay thin: they parse the request, call a service or selector, and render. Business rules can then be tested without HTTP.

## Design decisions and trade-offs

**Why a separate chat service instead of Django Channels?**
WebSocket connections are long-lived and mostly idle, which suits an async server well. Running them in a separate process lets the chat scale (and fail) independently of the request/response app. The cost is a second codebase, a second migration tool, and auth that has to cross the service boundary.

**How do the services share identity?**
Django issues a SimpleJWT access token when it renders the chat page. The chat service verifies it with the shared `SECRET_KEY` and only accepts `token_type == "access"`. Both services use the same PostgreSQL database: the chat service owns `chat_rooms`/`chat_messages` (Alembic) and reads Django's users table only to check that a room is opened with an approved trainer. This couples the services at schema level. It is a deliberate shortcut, and an internal API would be the next step if the services were split further.

**Why Redis Pub/Sub for the chat?**
Each chat instance only knows its own WebSocket connections. Publishing every message to Redis and having every instance fan it out lets the service run behind a load balancer with several replicas.

**Why are profile edits stored as a separate model?**
Live profiles must not change until an admin approves the change. `TrainerProfile` and `TrainerProfileUpdate` inherit the same abstract `TrainerProfileContent`, so the two can never drift apart. Approval copies `content_field_names()` instead of a hand-maintained list.

**Why Celery for e-mails?**
SMTP calls are slow and can fail. E-mails are queued with `transaction.on_commit`, so a worker never picks up a user that has not been committed yet (or was rolled back).

## Security notes

- No secrets in code: the app refuses to start without `SECRET_KEY`, `DEBUG` is off by default, and HTTPS/HSTS/secure cookies are enabled in production.
- Rich-text posts are sanitized server-side with [nh3](https://github.com/messense/nh3) using an allow-list that matches the editor, and user content in JS is rendered with `textContent`.
- State-changing endpoints are POST-only (CSRF-protected), the `next` redirect after login is validated, and the user-info API only returns data for trainers or your own chat partners (never e-mails).
- Rate limiting backed by Redis (django-ratelimit) on login, registration and content creation, plus server-side message size and rate limits in the chat.
- Password validators are enforced on registration and password reset.

## Running locally

```bash
cp .env.example .env        # fill in SECRET_KEY at least
docker compose up --build
```

The app runs at http://localhost:8000 and the chat service at http://localhost:8001. Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` to create a superuser on start. Demo data:

```bash
./scripts/seed_trainers.sh
./scripts/seed_posts.sh
```

## Tests and quality checks

Tests run against PostgreSQL, because the models use Postgres-only features such as `ArrayField`.

```bash
uv sync --all-packages
uv run ruff check .
uv run pytest                    # Django apps
cd chat && uv run pytest         # chat service (needs a `chat_test` database)
```

GitHub Actions runs lint, `manage.py check`, `makemigrations --check` and both test suites on every push and pull request.

## Known limitations / next steps

- Booking and calendar integration (Google Calendar API).
- Unread-message counters and notifications for the chat.
- Moving the chat service's read of the users table behind an internal API.
- Deployment pipeline (CD) to a cloud provider.
