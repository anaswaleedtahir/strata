# Adopt HackSoft Django Style Guide, adapted for HTMX

The codebase is server-rendered Django with HTMX, Channels, and forms — no DRF. We adopt the HackSoft Django Style Guide ([github.com/HackSoftware/Django-Styleguide](https://github.com/HackSoftware/Django-Styleguide)) for its **services / selectors / models / errors / tests** layer, but skip the DRF-shaped pieces (`apis.py`, `InputSerializer`/`OutputSerializer`, custom DRF exception handler). The guide's intent — keeping business logic out of views, forms, signals, and model `save()` — applies equally to template-rendering views and WebSocket consumers, so we apply it there. `apps/shared/` holds cross-app primitives (`BaseModel`, `ApplicationError`, validators); each app gains `services.py` + `selectors.py` + a `tests/` package.

## Considered Options

- **Full HackSoft including DRF migration** — rejected; introducing a REST surface alongside HTMX doubles the maintenance surface for no current product need.
- **Cherry-pick services/selectors only, skip BaseModel/tests/errors** — rejected; the layer is much weaker without the supporting conventions, and tests are already in poor shape (single 2502-line file in `chat/`).
- **Status quo** — rejected; views are growing past 600 lines with business logic, validations, and ORM queries interleaved.
