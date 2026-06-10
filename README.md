# Web Application for Trainers

This is a modern web application for trainers and users built with Django, PostgreSQL, and Docker. Dependency management is handled by `uv`.

## Project Structure

The structure of the application is designed to be modular and scalable:

```text
my_trainers_project/
├── core/                       # Main project configuration folder (settings, main urls)
├── apps/                       # All Django applications
│   ├── accounts/               # APP 1: User management and authentication logic
│   │   ├── migrations/         # Database migrations for accounts
│   │   └── templates/          # Account specific templates (login, register, emails)
│   ├── trainers/               # APP 2: Trainer profiles, directory, and search engine logic
│   │   ├── migrations/         # Database migrations for trainers
│   │   └── templates/          # Trainer specific templates (dashboards, search, forms)
│   └── pages/                  # APP 3: Static pages logic (About, Contact, Privacy Policy)
│       └── templates/          # Page specific templates
├── templates/                  # Global folder for base HTML templates
│   └── includes/               # Reusable template components (header, footer)
├── static/                     # Project static files
│   └── css/                    # Custom CSS styles (Tailwind config output)
└── media/                      # User-uploaded files (requires configuration in settings.py)
    └── profile_pics/           # Trainer profile pictures
```

### Key Modules

- **core**: The core configuration for the entire application, containing settings and the primary URL dispatcher.
- **apps/accounts**: Responsible for user authentication flows, profile management, and session handling.
- **apps/trainers**: A dedicated module for finding and presenting trainer profiles, managing their multimedia (like photos), and handling trainer submissions.
- **apps/pages**: Handles static and semi-static pages such as About, Contact, and Privacy Policy.
- **templates/static**: Location for global base HTML files, reusable components, and static assets (CSS, JS, Images). App-specific templates reside in their respective `apps/<app_name>/templates/` directories.
- **media**: Where all user-provided data and photos reside (not committed to source control).
