# Adopt project-owned shadcn UI primitives

Strata replaces DaisyUI with stock shadcn-style components scaffolded by `shadcn_django` into Django Cotton templates. The generated templates are project-owned source, not a runtime dependency; Tailwind remains Node-free through `django-tailwind-cli`, Alpine and HTMX retain interactive behavior, and the complete user-facing site migrates before DaisyUI is removed.

## Consequences

- Upstream component updates are reviewed and copied deliberately rather than inherited automatically.
- Entrance effects use Tailwind's built-in utilities; no animation library is vendored.
- Django Unfold remains the independent admin design system.
