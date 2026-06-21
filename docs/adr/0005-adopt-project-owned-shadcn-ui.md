# Adopt project-owned shadcn UI primitives

Strata replaces DaisyUI with stock shadcn-style components scaffolded by `shadcn_django` into Django Cotton templates. The generated templates are project-owned source, not a runtime dependency; Tailwind remains Node-free through `django-tailwind-cli`, Alpine and HTMX retain interactive behavior, and the complete user-facing site migrates before DaisyUI is removed.

## Consequences

- Upstream component updates are reviewed and copied deliberately rather than inherited automatically.
- `tw-animate-css` is vendored as CSS so production builds do not require npm.
- Django Unfold remains the independent admin design system.
