# Web Application for Trainers

This is a modern web application for trainers and users built with Django, PostgreSQL, and Docker. Dependency management is handled by `uv`.

<img width="1080" height="1920" alt="Image" src="https://github.com/user-attachments/assets/591990cb-0010-4334-a7e1-a5628a589892" />

## 🌟 Key Features

* **🧠 AI Sport Matcher (Trener AI):** An interactive, step-by-step quiz powered by the **Google Gemini API** (`gemini-3.5-flash`). It asks users 13 carefully curated questions (including an open-ended feedback section) regarding their goals, budget, physical condition, and preferences. Based on the answers, the AI acts as a professional coach, providing a personalized and highly motivating sport recommendation. 
<img width="389" height="642" alt="Image" src="https://github.com/user-attachments/assets/f0d976ef-19ec-42b4-9bd1-56f4e23e6a96" />

* **🔍 Advanced Trainer Search:** A robust search engine allowing users to filter trainers by sport, location, and training type (Online/Stationary).
* **👤 Professional Profiles:** Dedicated profile pages for trainers to showcase their skills, bio, and pictures.
* **🔐 Google Social Authentication:** Seamless and secure sign-up and login process utilizing OAuth 2.0 via Google, providing users with a frictionless authentication experience.

<img width="1920" height="1080" alt="Image" src="https://github.com/user-attachments/assets/85377786-9a74-4779-aaeb-b59ed7bee0b2" />

* **✍️ Trainer Publications (Knowledge Base):** An integrated blogging system allowing trainers to publish articles and share their expertise. Includes a dedicated "Knowledge Base" hub with search capabilities, paginated views, and seamless integration with trainer profiles.

<img width="1266" height="1218" alt="Image" src="https://github.com/user-attachments/assets/a9f55de7-efc0-471a-9588-6fc81737fa8f" />

## 🐳 Docker Containers

The project is orchestrated using `docker-compose` and consists of 5 main containers:

1. **`web`**: The main Django application running on Gunicorn/Uvicorn, handling all standard HTTP requests, templates, and REST APIs.
2. **`db`**: A PostgreSQL 15 database container persisting data for the application.
3. **`redis`**: An in-memory data structure store used as a message broker for Celery and for caching rate-limits.
4. **`celery_worker`**: A background worker executing asynchronous tasks (e.g., sending activation emails) to avoid blocking the main `web` threads.
5. **`chat`**: A standalone ASGI microservice built with **FastAPI** that exclusively handles real-time WebSocket connections and chat history using Redis Pub/Sub for scalability.

## Project Structure

The application follows a project-level architecture pattern (sometimes referred to as a monorepo-style Django structure or apps-as-packages layout).
Currently, the application consists of 4 main apps:

```text
apps/
├── accounts/               # APP 1: User management and authentication logic
├── admin_dashboard/        # APP 2: Custom administration dashboard logic
├── pages/                  # APP 3: Static pages logic (About, Contact, Privacy Policy)
└── trainers/               # APP 4: Trainer profiles, directory, search engine and AI recommendations
```

### App Structure Template

Each app follows a strict separation of concerns, heavily utilizing the **Service Layer** and **Selectors** pattern to keep views and models thin:

```text
apps/<app_name>/
├── __init__.py
├── admin.py                # Django admin configuration
├── apps.py                 # App configuration
├── forms.py                # Form definitions
├── models.py               # Database schema definitions (keep logic out of here)
├── selectors.py            # Data fetching logic (complex queries, filtering)
├── services.py             # Business logic and writing to the database
├── urls.py                 # URL routing for the app
└── views.py                # HTTP request handling (orchestrates forms, services, and selectors)
```

By separating `services.py` (which handles business logic, object creation, and updates) from `selectors.py` (which handles data retrieval and complex queries), the codebase remains highly maintainable, testable, and clean.

### Key Modules

- **core**: The core configuration for the entire application, containing settings and the primary URL dispatcher.
- **apps/accounts**: Responsible for user authentication flows, profile management, and session handling.
- **apps/admin_dashboard**: Provides a custom admin interface for platform management.
- **apps/pages**: Handles static and semi-static pages such as About, Contact, and Privacy Policy.
- **apps/trainers**: A dedicated module for finding and presenting trainer profiles, managing their multimedia (like photos), AI features, and handling trainer submissions.
- **templates/static**: Location for global base HTML files, reusable components, and static assets (CSS, JS, Images). App-specific templates reside in their respective `apps/<app_name>/templates/` directories.
- **media**: Where all user-provided data and photos reside (not committed to source control).

## 🏗️ Architecture & Security Showcase

### 1. Background Tasks (Celery + Redis)
To ensure the application is scalable, highly responsive, and robust, **Celery** combined with **Redis** as a message broker is used to handle long-running background tasks. 
* **Why this approach?** In standard synchronous Django views, triggering an email (e.g. account activation) freezes the user's HTTP request until the SMTP server successfully processes the email. This blocks the web thread and creates a poor user experience. 
* **The Solution:** By decoupling email logic using the `@shared_task` decorator and `.delay()`, the application immediately acknowledges the registration and delegates the email sending process to a separate Celery worker running in the background. This is a common and highly valued pattern in mid/senior-level backend architecture, emphasizing separation of concerns and non-blocking I/O.

### 2. Rate Limiting & Security
To protect the application against Brute Force attacks, Credential Stuffing, and spam, a robust rate-limiting mechanism is implemented using the `django-ratelimit` library backed by a **Redis** cache.
* **Global Cache Strategy:** Instead of relying on local memory (which resets and doesn't scale across multiple Gunicorn workers), the application uses the Redis container to accurately track request counts globally.
* **Granular View Protection:** Specific limits are applied to vulnerable endpoints:
  - **Authentication:** Max 5 login attempts per minute per IP, and max 5 attempts per specific username.
  - **Registration:** Strictly limited to prevent bot-driven spam accounts.
  - **Content Creation:** Limits applied to posting and updating profiles to prevent API abuse.
* **Custom Middleware Handling:** When a user hits the limit, a custom Django Middleware intercepts the `Ratelimited` exception and gracefully redirects them to a dedicated, user-friendly 429 Error Page rather than throwing a raw 403 Forbidden error.

## 🚀 Future Roadmap & Development Ideas 

1. **Real-time Chat & WebSockets (Django Channels):** 
   - Allow users to directly message trainers on the platform. 
   - Implementing this demonstrates knowledge of asynchronous Python, ASGI, Redis, and real-time bidirectional communication.
2. **Booking & Calendar System with External API Integration:**
   - A feature for users to schedule training sessions directly through the app.
   - Syncing it with the **Google Calendar API** would showcase complex business logic handling, dealing with timezones, scheduling conflicts, and third-party API integrations.managing secure user data.
3. **CI/CD Pipeline & Scalable Cloud Deployment:**
   - Setting up **GitHub Actions** for automated testing and linting, and deploying the Dockerized application to a cloud provider like **AWS (ECS/EC2)** or **DigitalOcean**.
   - Connecting an external **S3 Bucket** for handling media files instead of local storage. 
