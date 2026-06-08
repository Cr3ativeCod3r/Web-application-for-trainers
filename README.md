# Web Application for Trainers

This is a modern web application for trainers and users built with Django, PostgreSQL, and Docker. Dependency management is handled by `uv`.

## Project Structure

The structure of the application is designed to be modular and scalable:

```text
my_trainers_project/
│
├── manage.py                   # Main project management file
├── .env                        # Environment variables (database passwords, SECRET_KEY, DEBUG mode)
│
├── core/                       # Main project configuration folder (formerly 'config')
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py             # Main project settings
│   ├── urls.py                 # Main URL routing (including URLs from other apps)
│   └── wsgi.py
│
├── accounts/                   # APP 1: User management and authentication
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                # Login and registration forms
│   ├── models.py               # Custom user model (e.g., CustomUser)
│   ├── urls.py                 # URLs for login, logout, password reset
│   └── views.py                # Authentication views
│
├── trainers/                   # APP 2: Trainer profiles, directory, and search engine
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py                # Approving trainer applications via the Django admin panel
│   ├── apps.py
│   ├── forms.py                # Application form, photo upload forms
│   ├── models.py               # Models: TrainerProfile, TrainerPhoto (limit up to 8 photos)
│   ├── urls.py                 # URLs for search, trainer details, application page
│   └── views.py                # Views: Home (Search), Trainer Detail, Apply Form
│
├── templates/                  # Global folder for HTML templates
│   ├── base.html               # Main template (header, footer, navigation)
│   ├── accounts/
│   │   ├── login.html
│   │   └── register.html
│   └── trainers/
│       ├── home_search.html    # Homepage with filters (like OLX)
│       ├── trainer_detail.html # Trainer's public profile page
│       └── trainer_apply.html  # Form for trainers to submit their details
│
├── static/                     # Project static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── scripts.js
│   └── img/                    # Static graphics (logo, backgrounds)
│
└── media/                      # User-uploaded files (requires configuration in settings.py)
    └── trainer_photos/         # Trainer photos will be stored here
```

### Key Modules

- **core**: The core configuration for the entire application, containing settings and the primary URL dispatcher.
- **accounts**: Responsible for user authentication flows, profile management, and session handling.
- **trainers**: A dedicated module for finding and presenting trainer profiles, managing their multimedia (like photos), and handling trainer submissions.
- **templates/static**: Centralized location for the HTML files and static assets (CSS, JS, Images).
- **media**: Where all user-provided data and photos reside (not committed to source control).
