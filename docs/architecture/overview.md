# Architecture Overview

## System Architecture

Property Hub is a modern Django-based real estate management platform with a component-based architecture.

## Technology Stack

### Backend
- **Django 6.0.2** - Web framework
- **Python 3.13+** - Programming language
- **PostgreSQL 17** - Primary database
- **Redis** - Caching and WebSocket channel layer
- **Channels** - WebSocket support for real-time features
- **UV** - Fast Python package manager

### Frontend
- **Tailwind CSS 4** - Utility-first CSS framework built by `django-tailwind-cli`
- **DaisyUI** - Component library built on Tailwind
- **Django Cotton** - Reusable template components
- **HTMX** - Dynamic HTML interactions without JavaScript
- **Alpine.js** - Lightweight JavaScript framework
- **WhiteNoise** - Static file serving with compression

### Infrastructure
- **Docker** - Containerization
- **AWS S3** - Media file storage
- **Localstack** - Local AWS simulation for development

## Application Structure

### Django Apps

```
apps/
├── properties/     # Property listings and management
├── users/          # User authentication and profiles
├── chat/           # Real-time chat functionality
└── shared/         # Shared utilities and base classes
```

Each app follows Django's standard structure:
- `models.py` - Database models
- `views.py` - View logic
- `forms.py` - Form definitions
- `urls.py` - URL routing
- `admin.py` - Admin interface configuration

### Configuration

```
config/
├── settings/
│   ├── base.py         # Base settings for all environments
│   ├── development.py  # Development-specific settings
│   └── production.py   # Production-specific settings
├── urls.py             # Root URL configuration
├── wsgi.py             # WSGI application
├── asgi.py             # ASGI application (for WebSockets)
└── routing.py          # WebSocket routing
```

### Templates

```
templates/
├── _layouts/       # Base layouts (base.html, etc.)
├── cotton/         # Shared Cotton components
├── properties/     # Property-specific templates
├── users/          # User-specific templates
└── chat/           # Chat-specific templates
```

**Component-Based Approach:**
- Reusable shared components in `templates/cotton/`
- Property-specific components in `apps/properties/templates/cotton/properties/`
- DRY principle for forms, navigation, UI elements
- Separation of layouts, components, and pages

### Static Files

See [Frontend Architecture](./frontend.md) for detailed information.

```
assets/css/         # Tailwind source CSS
static/             # Static assets and generated CSS output
staticfiles/        # Collected files (auto-generated)
```

## Design Patterns

### App-Based Organization
- Domain-driven design with separate apps
- Clear separation of concerns
- Each app is self-contained and reusable
- Shared utilities in `apps/shared/`

Each app follows the [HackSoftware Django Style Guide](https://github.com/HackSoftware/Django-Styleguide):

```
apps/<app>/
├── models.py      # Data layer only — no business logic
├── services.py    # All writes: create/update/delete, raises ApplicationError
├── selectors.py   # All reads: pure query functions, no mutation
├── forms.py       # I/O shape only: field validation, no DB queries, no .save()
├── views.py       # Thin: call form → call service/selector → render
├── urls.py
└── admin.py
```

**Services** (`services.py`):
- Keyword-only arguments (`def foo(*, param)`)
- Call `full_clean()` before every `.save()`
- Raise `ApplicationError` for domain violations
- Wrap multi-step writes in `transaction.atomic()`

**Selectors** (`selectors.py`):
- Pure reads — never mutate state
- Return QuerySets or plain values
- Named `<entity>_<query>` (e.g. `property_list_published`)

**Forms** (`forms.py`):
- Validate field shape/format only (email format, passwords match)
- No database queries, no uniqueness checks — those belong in services
- Never call `.save()` when a service exists

**Shared infrastructure** (`apps/shared/`):
- `BaseModel`: abstract model with `created_at` (db_index=True) + `updated_at`
- `ApplicationError`: domain exception with `message: str` + optional `extra: dict`

### Component-Based Templates
- Reusable UI components
- Consistent design system
- Easy to maintain and update
- DRY principle

### Settings Organization
- Base settings for all environments
- Environment-specific overrides
- Secrets managed via environment variables
- 12-factor app methodology

## Data Flow

### Request/Response Cycle

```
Browser → Django URL Router → View → Template → Response
                                ↓
                            Database
```

### WebSocket Flow (Chat)

```
Browser ← WebSocket → Channels → Redis → Channels → WebSocket → Browser
                         ↓
                     Database
```

## Security

### Authentication
- Custom User model extending AbstractUser
- Django's built-in authentication system
- Django Axes for brute-force protection
- Session-based authentication

### Authorization
- Django's permission system
- Model-level permissions
- View-level decorators
- Template-level checks

### Security Features
- CSRF protection enabled
- XSS protection via template escaping
- SQL injection prevention via ORM
- Secure password hashing (PBKDF2)
- HTTPS enforcement in production
- Security middleware enabled

## Performance

### Caching Strategy
- Redis for session storage
- Template fragment caching
- Database query optimization
- Static file compression (WhiteNoise)

### Database Optimization
- Indexed fields for common queries
- Select/prefetch related for N+1 prevention
- Database connection pooling
- Query optimization

### Static Files
- WhiteNoise for efficient serving
- Gzip compression
- Cache-busting via hashed filenames
- CDN-ready architecture

## Scalability

### Horizontal Scaling
- Stateless application design
- Session storage in Redis
- Media files in S3
- Database connection pooling

### Vertical Scaling
- Efficient database queries
- Caching strategy
- Async task processing (future)
- WebSocket connection management

## Development Workflow

### Local Development
1. Docker Compose for services (PostgreSQL, Redis, Localstack)
2. Local ASGI server via uvicorn (`just runserver` or `just uvicorn`)
3. Tailwind CSS watch mode through `django-tailwind-cli` (`just tailwind-watch`)
4. Hot reload for templates

### Testing
- Plain `django.test.TestCase` (sync) or `TransactionTestCase` (async/WebSocket)
- `factory_boy` for test data — factories in `apps/<app>/tests/factories.py`
- Tests split by layer: `test_services.py`, `test_views.py`, `test_consumers.py`, `test_admin.py`
- Run with SQLite: `DATABASE_URL=sqlite:///test.db python manage.py test`
- Frontend tests for JavaScript
- E2E tests (future)

### Deployment
- Docker multi-stage builds
- Environment-based configuration
- Automated static file collection
- Health checks

## Future Enhancements

### Planned Features
- Celery for async task processing
- Full-text search (PostgreSQL or Elasticsearch)
- API endpoints (Django REST Framework)
- Mobile app support
- Advanced analytics

### Technical Improvements
- Comprehensive test coverage
- CI/CD pipeline
- Monitoring and logging
- Performance optimization
- API documentation

## Related Documentation

- [Frontend Architecture](./frontend.md) - Frontend structure and build process
- [Backend Architecture](./backend.md) - Detailed backend architecture *(Coming Soon)*
- [Database Schema](./database.md) - Database models and relationships *(Coming Soon)*
- [Deployment Checklist](../deployment/checklist.md) - Production deployment guide
