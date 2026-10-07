# Coachly

A marketplace for sports trainers: clients search for trainers by sport, location and training type, chat with them in real time, read their articles, and can take an AI quiz that suggests a sport. Trainers apply, get moderated by an admin, and manage their profile and publications.

<img width="1080" height="1920" alt="Home page" src="https://github.com/user-attachments/assets/591990cb-0010-4334-a7e1-a5628a589892" />

**Stack:** Django 6 · PostgreSQL 15 (one database per service) · Celery + Redis (broker, Streams, Pub/Sub) · FastAPI (WebSockets) · SQLAlchemy 2 (async) + Alembic · Google Gemini API · Cloudflare R2 · Docker Compose · uv · pytest · GitHub Actions

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
                 session + CSRF                      ┌───────────────────────┐
 Browser ───────────────────────▶ Django (web) ─────▶│ PostgreSQL "trainapp" │
   │  ▲   POST /api/chat/token/   gunicorn           │ users, profiles,      │
   │  │   ◀── ES256 token (5 min)    │               │ posts, outbox_event   │
   │  │                              │ on_commit     └───────────▲───────────┘
   │  │                              ▼                           │ SKIP LOCKED
   │  │                       Celery worker / beat ──────────────┘
   │  │                              │ XADD coachly.users.v1
   │  │                              ▼
   │  │                       ┌──────────────┐   Streams (consumer group)
   │  │                       │    Redis     │──────────────────────────┐
   │  │                       │ broker,      │◀── Pub/Sub: messages,    │
   │  │                       │ rate limits, │    control (kick user)   │
   │  │                       │ WS tickets   │                          ▼
   │  │                       └──────▲───────┘                 ┌───────────────────┐
   │  └── REST (Bearer) ─────────────┼────────── chat (FastAPI)│ PostgreSQL "chat" │
   └───── WebSocket (?ticket=) ──────┘           + uvicorn ───▶│ rooms, messages,  │
                                                               │ chat_users (copy) │
                                                               └───────────────────┘
```

| Container | Responsibility |
|---|---|
| `web` | Django app: pages, forms, admin dashboard, issues chat tokens |
| `db` | PostgreSQL owned by the Django app |
| `chat` | FastAPI service: WebSockets, chat history, its own copy of user data |
| `chat_db` | PostgreSQL owned by the chat service (nothing else connects to it) |
| `redis` | Celery broker, rate-limit cache, event stream, chat Pub/Sub, WebSocket tickets |
| `celery_worker` | E-mails and the outbox relay |
| `celery_beat` | Periodic outbox relay (safety net) and outbox clean-up |

<img width="6330" height="5054" alt="Architecture diagram" src="https://github.com/user-attachments/assets/ac177999-e970-4a07-9fb6-cf1cd40630a9" />

### Code layout

```text
apps/
├── accounts/         # users, registration/activation, login, trainer lifecycle, chat tokens, user events
├── trainers/         # profiles, moderation flow, search, posts
├── pages/            # static pages, knowledge base, AI quiz
└── admin_dashboard/  # moderation UI
├── events/           # transactional outbox + relay to Redis Streams
core/                 # settings, URLs, middleware, HTML sanitizer
chat/                 # FastAPI microservice (own database, Alembic migrations, stream consumer, tests)
```

Inside an app, **`services.py`** holds operations that change state (wrapped in transactions), **`selectors.py`** holds read queries, and views stay thin: they parse the request, call a service or selector, and render. Business rules can then be tested without HTTP.

## Design decisions and trade-offs

**Why a separate chat service instead of Django Channels?**
WebSocket connections are long-lived and mostly idle, which suits an async server well. Running them in a separate process lets the chat scale (and fail) independently of the request/response app. The cost is a second codebase, a second migration tool, and auth that has to cross the service boundary.

**Why does each service have its own database?**
Earlier the chat service read Django's users table and Django read the chat's rooms table. Any migration on one side could break the other at runtime, and neither could be scaled, restored or moved separately. Now each service owns its schema and talks to the other only through published contracts: the chat service keeps a local copy of the user data it needs (`chat_users`) and returns partner details itself, so Django never has to look at chat data.

**How does user data reach the chat service?** (transactional outbox + Redis Streams)
1. Any change to a user or profile (services, Django admin, allauth) triggers a signal that writes a full public snapshot of the user into `events_outboxevent`, *in the same transaction* as the change. Publishing to Redis directly from the request would either lose the event (crash after commit) or announce a change that was rolled back.
2. After commit, a Celery task relays unpublished rows to the `coachly.users.v1` stream (rows are claimed with `SELECT ... FOR UPDATE SKIP LOCKED`, so several workers can relay safely). Celery beat re-runs the relay every 15 s in case the broker was briefly down.
3. The chat service reads the stream through a consumer group and upserts `chat_users` only if the event id is newer than the stored version. Delivery is at-least-once; replays and out-of-order entries are harmless. Entries left pending by a crashed instance are claimed after a minute.
4. If a user becomes inactive (ban, deletion), the consumer publishes a control message and every chat instance closes that user's open WebSockets.

The trade-off is eventual consistency: a just-approved trainer can receive messages a moment later (normally well under a second). `python manage.py publish_user_snapshots` re-sends everyone, which bootstraps a fresh chat database and repairs drift.

**How is the chat authenticated?**
- Django signs a 5-minute token with an **ES256 private key**; the chat service only has the **public key**, so a compromised chat service cannot mint tokens. Tokens carry `iss`/`aud`, and the verifier pins the algorithm (no HS256-with-public-key confusion).
- The page fetches tokens on demand from `POST /api/chat/token/` (session + CSRF) instead of having a long-lived token embedded in the HTML.
- Browsers cannot set headers on a WebSocket, and a token in the URL ends up in access logs. The page exchanges its token for a **one-time ticket** (30 s, consumed with an atomic `GETDEL`) and connects with that.
- A valid token is not enough: every request and connection also requires the account to be active in `chat_users`, so a ban takes effect immediately instead of when the token expires.

**Why is the trainer status a state machine?**
Approving an application and lifting a ban both end in `APPROVED_TRAINER`, but from different states. The transitions (`apply`, `approve`, `ban`, `unban`) are named and checked against their source status under a row lock, so two admins acting at once cannot produce an impossible state.

**Why Redis Pub/Sub for the chat?**
Each chat instance only knows its own WebSocket connections. Publishing every message to Redis and having every instance fan it out lets the service run behind a load balancer with several replicas. Everything else that must hold across instances (message rate limit per user, WebSocket tickets) lives in Redis too, not in process memory.

**Why are profile edits stored as a separate model?**
Live profiles must not change until an admin approves the change. `TrainerProfile` and `TrainerProfileUpdate` inherit the same abstract `TrainerProfileContent`, so the two can never drift apart. Approval copies `content_field_names()` instead of a hand-maintained list.

**Why Celery for e-mails?**
SMTP calls are slow and can fail. E-mails are queued with `transaction.on_commit`, so a worker never picks up a user that has not been committed yet (or was rolled back).

## Security notes

- No secrets in code: the app refuses to start without `SECRET_KEY`, `DEBUG` is off by default, and HTTPS/HSTS/secure cookies are enabled in production.
- Rich-text posts are sanitized server-side with [nh3](https://github.com/messense/nh3) using an allow-list that matches the editor, and user content in JS is rendered with `textContent`.
- State-changing endpoints are POST-only (CSRF-protected) and the `next` redirect after login is validated. Events sent to other services contain public profile data only, never e-mails.
- Rate limiting backed by Redis (django-ratelimit) on login, registration, token issuing and content creation; in the chat, message size limits and a per-user message rate shared by all tabs and instances.
- Chat tokens: see "How is the chat authenticated?" above. Post content is capped at 2 MB.
- Password validators are enforced on registration and password reset.

## Running locally

```bash
cp .env.example .env              # fill in SECRET_KEY at least
./scripts/generate_jwt_keys.sh    # ES256 key pair for chat tokens -> ./secrets (git-ignored)
docker compose up --build
```

The app runs at http://localhost:8000 and the chat service at http://localhost:8001. Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` to create a superuser on start. On start the web container also queues a snapshot of every user, so the chat service's user copy is filled even on a fresh `chat_db`. Demo data:

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
cd chat && uv run pytest         # chat service; database from CHAT_TEST_DATABASE_URL
```

GitHub Actions runs lint, `manage.py check`, `makemigrations --check` and both test suites on every push and pull request, with the chat suite on its own PostgreSQL server.

### Upgrading an existing deployment

Before this layout the chat tables lived in the main database. Stop the chat service, run `scripts/move_chat_tables.sh` (copies `chat_rooms`/`chat_messages` to the chat database and drops them from the main one), start the chat service and run `python manage.py publish_user_snapshots`.

## Known limitations / next steps

- Booking and calendar integration (Google Calendar API).
- Unread-message counters and notifications for the chat.
- A dead-letter stream and metrics (consumer lag, outbox backlog) for the event pipeline.
- Key rotation for chat tokens (`kid` header + several public keys on the verifier side).
- Deployment pipeline (CD) to a cloud provider.
