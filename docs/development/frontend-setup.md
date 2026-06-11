# Frontend Development Setup

This guide covers day-to-day UI development in Property Hub.

## Setup

Install Python dependencies:

```bash
just build
```

Start supporting services:

```bash
just up
```

Run Django with Tailwind watch mode:

```bash
just runserver
```

## Working With Tailwind

Tailwind CSS source lives in:

```text
assets/css/input.css
```

Use utility classes directly in Django templates first. Add custom CSS in `assets/css/input.css` only when a utility composition is reused enough to justify it.

Production CSS build:

```bash
uv run python manage.py tailwind build --force
```

Verbose build for troubleshooting:

```bash
uv run python manage.py tailwind build --force --verbose
```

## Working With Cotton Components

Shared reusable components live in:

```text
templates/cotton/
```

Property-specific reusable components live in:

```text
apps/properties/templates/cotton/properties/
```

Keep layouts and pages as regular Django templates. Convert only reusable pieces into Cotton components.

Examples:

```django
<c-navigation.navbar />
<c-ui.pagination :page_obj="page_obj" />
<c-forms.field :field="form.email" label="Email" placeholder="Enter your email" required />
<c-properties.favorite-button :property="property" />
```

Form components should keep explicit props for label, placeholder, required state, icon, rows, and help text.

## JavaScript

HTMX and Alpine.js are loaded from pinned CDN URLs with SRI in `templates/_layouts/base.html`.

Project-owned JavaScript lives in `static/js/` and is served directly by Django. The chat client is:

```text
static/js/chat-client.js
```

Browser tests for the chat client live in:

```text
docs/development/chat-client-test.html
docs/development/chat-client-test.js
```

## Static Files

Build CSS and collect static files before deployment:

```bash
uv run python manage.py tailwind build --force
uv run python manage.py collectstatic --noinput
```

Generated output:

```text
static/dist/output.css
staticfiles/
```

Do not edit generated files in `staticfiles/`.

## Best Practices

- Prefer Tailwind utilities over custom CSS.
- Keep custom CSS in `assets/css/input.css`.
- Keep static browser JavaScript in `static/js/`.
- Use Cotton for reusable components only.
- Keep page-level templates in `templates/<app>/` or app template directories.
- Run `uv run python manage.py tailwind build --force` before checking deployment CSS.

## Related Documentation

- [Frontend Architecture](../architecture/frontend.md)
- [Chat Client](./chat-client.md)
- [Deployment Checklist](../deployment/checklist.md)
