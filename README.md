# Web Application for Trainers

This is a modern web application for trainers and users built with Django, PostgreSQL, and Docker. Dependency management is handled by `uv`.

## Project Structure

The structure of the application is designed to be modular and scalable:

```text
my_trainers_project/
├── core/                       # Main project configuration folder (settings, main urls)
├── accounts/                   # APP 1: User management and authentication logic
│   └── migrations/             # Database migrations for accounts
├── trainers/                   # APP 2: Trainer profiles, directory, and search engine logic
│   └── migrations/             # Database migrations for trainers
├── pages/                      # APP 3: Static pages logic (About, Contact, Privacy Policy)
├── templates/                  # Global folder for HTML templates
│   ├── accounts/               # Templates for authentication (login, register)
│   ├── trainers/               # Templates for trainer profiles, dashboards and search
│   ├── pages/                  # Templates for static pages
│   ├── emails/                 # Templates for email messages
│   └── includes/               # Reusable template components (header, footer)
├── static/                     # Project static files
│   └── css/                    # Custom CSS styles (Tailwind config output)
└── media/                      # User-uploaded files (requires configuration in settings.py)
    └── profile_pics/           # Trainer profile pictures
```

### Key Modules

- **core**: The core configuration for the entire application, containing settings and the primary URL dispatcher.
- **accounts**: Responsible for user authentication flows, profile management, and session handling.
- **trainers**: A dedicated module for finding and presenting trainer profiles, managing their multimedia (like photos), and handling trainer submissions.
- **templates/static**: Centralized location for the HTML files and static assets (CSS, JS, Images).
- **media**: Where all user-provided data and photos reside (not committed to source control).
