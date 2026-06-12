# RealmKey

A modern real-estate property management platform built with Django, featuring a component-based architecture for listing, searching, and managing properties.

---

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](./docs/) directory:

- **[Architecture](./docs/architecture/)** - System design and technical decisions
- **[Development](./docs/development/)** - Development guides and workflows
- **[Deployment](./docs/deployment/)** - Production deployment guides
- **[Guides](./docs/guides/)** - Step-by-step tutorials

**Quick Links:**
- [Architecture Overview](./docs/architecture/overview.md)
- [Frontend Architecture](./docs/architecture/frontend.md)
- [Frontend Setup Guide](./docs/development/frontend-setup.md)
- [Deployment Checklist](./docs/deployment/checklist.md)

---

## 🛠 Tech Stack

### Backend
- **Django 6.0.2** - Web framework
- **Python 3.13+** - Programming language
- **PostgreSQL-17** - Database
- **UV** - Package manager

### Frontend
- **Tailwind CSS 4** - Utility-first CSS framework, built by Django
- **DaisyUI** - Component library
- **Django Cotton** - Reusable template components
- **HTMX** - Dynamic interactions
- **Alpine.js** - Lightweight JavaScript framework

### Infrastructure
- **Docker** - Containerization
- **AWS S3** - Media storage
- **Localstack** - Local AWS simulation

---

## 🏗 Architecture

### Project Structure

```
realm-key/
├── apps/
│   ├── properties/          # Property management
│   │   ├── models.py        # Property, PropertyImage models
│   │   ├── views.py         # View logic
│   │   ├── forms.py         # Form definitions
│   │   └── urls.py          # URL routing
│   ├── users/               # User authentication
│   │   ├── models.py        # User model
│   │   ├── views.py         # Auth views
│   │   └── forms.py         # Auth forms
│   └── shared/              # Shared utilities
│
├── config/                  # Project configuration
│   ├── settings/            # Environment-specific settings
│   │   ├── base.py          # Base settings
│   │   ├── development.py   # Development settings
│   │   └── production.py    # Production settings
│   ├── urls.py              # Root URL config
│   └── wsgi.py              # WSGI config
│
├── templates/               # HTML templates
│   ├── _layouts/            # Base layouts
│   ├── cotton/              # Shared Cotton components
│   ├── properties/          # Property templates
│   └── users/               # User templates
│
├── assets/                  # Source assets
│   └── css/
│       └── input.css        # Tailwind CSS 4 source
│
├── static/                  # Production static assets
│   ├── dist/                # Compiled CSS
│   ├── images/              # Images
│   └── js/                  # Static JavaScript
│
├── staticfiles/             # Collected static files (generated)
├── media/                   # User uploads
├── Dockerfile               # Docker image
├── docker-compose.*.yml     # Docker compose configs
├── pyproject.toml           # Python dependencies
└── justfile                 # Development commands
```

### Design Patterns

**Component-Based Templates**
- Reusable UI components in `templates/cotton/`
- Separation of layouts, components, and pages
- DRY principle for forms, navigation, and UI elements

**App-Based Organization**
- Domain-driven design with separate apps
- Clear separation of concerns
- Modular and maintainable codebase

**Modern Frontend Stack**
- Utility-first CSS with Tailwind
- Progressive enhancement with HTMX
- Minimal JavaScript with Alpine.js
- Components from DaisyUI

---

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd realm-key
   ```

2. **Set up environment variables**
   ```bash
   cp .env.sample .env.dev
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   # Install Python dependencies
   just build
   ```

4. **Run all the dev services in Docker**
   ```bash
   # Start all services PostgresDB, Redis, Mailhog and Localstack
   just up
   ```

5. **Run database migrations**
   ```bash
   just migrate
   ```

6. **Start development server**
   ```bash
   just runserver
   ```

7. **Access the application**
   ```
   http://127.0.0.1:8000
```

---

## 🔧 Development Commands

### Just Commands

| Command | Description |
|---------|-------------|
| `just build` | Install Python dependencies |
| `just migrate` | Apply Django migrations |
| `just makemigrations` | Create new Django migrations |
| `just runserver [port]` | Start uvicorn with Tailwind watch mode (default port: 8000) |
| `just uvicorn [port]` | Start uvicorn only (ASGI + WebSocket support) |
| `just tailwind-watch` | Start Tailwind watch mode only |
| `just build-css` | Build production Tailwind CSS |
| `just up` | Start development services i.e (PostgresDB, Redis, Localstack and Mailhog) with Docker |
| `just down` | Stop development services |
| `just help` | Show all available commands |

---

## 🔐 Environment Configuration

Your `.env` file will have the following variables:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database
DATABASE_URL=sqlite:///db.sqlite3

# AWS S3 (Localstack for local deelopment)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_MEDIA_BUCKET_NAME=your-bucket-name
```

---

## 🎨 Frontend Development

The frontend uses Tailwind CSS 4 with DaisyUI for styling, Django Cotton for reusable template components, and pinned CDN HTMX/Alpine scripts for browser behavior.

**Quick Start:**
```bash
just runserver           # uvicorn plus Tailwind watch mode
just build-css           # Production Tailwind build
```

**Learn More:**
- [Frontend Architecture](./docs/architecture/frontend.md) - Architecture and design decisions
- [Frontend Setup Guide](./docs/development/frontend-setup.md) - Development workflow and best practices

**Custom Theme:**
- Primary: Indigo (#6366f1)
- Secondary: Purple (#d946ef)
- Accent: Orange (#f97316)

---

## 🧪 Testing

In Progress

---

## 📦 Deployment

**Quick Deploy:**
```bash
docker build -t realm-key .
docker-compose -f docker-compose.prod.yml up
```

**Complete Guide:**
See the [Deployment Checklist](./docs/deployment/checklist.md) for detailed production deployment instructions.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/guides/contributing.md) for details.

**Quick Start:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit using conventional format (`Add: new feature`)
5. Push and create a Pull Request

See [Contributing Guide](./docs/guides/contributing.md) for detailed guidelines on code style, testing, and documentation.

---

## 📚 Resources

### Project Documentation
- [Documentation Index](./docs/README.md)
- [Architecture Overview](./docs/architecture/overview.md)
- [Frontend Guide](./docs/development/frontend-setup.md)
- [Deployment Guide](./docs/deployment/checklist.md)

### External Resources
- [Django Documentation](https://docs.djangoproject.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [DaisyUI Documentation](https://daisyui.com/)
- [HTMX Documentation](https://htmx.org/docs/)
- [Alpine.js Documentation](https://alpinejs.dev/)
