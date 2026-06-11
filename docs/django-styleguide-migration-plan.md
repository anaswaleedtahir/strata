# Django Style Guide migration plan

Adopt HackSoft Django Style Guide ([github.com/HackSoftware/Django-Styleguide](https://github.com/HackSoftware/Django-Styleguide)), adapted for the HTMX + Channels stack (no DRF). See [ADR-0001](./adr/0001-adopt-hacksoft-styleguide-htmx-adapted.md) for the framing decision.

## Locked decisions (from grilling session)

| # | Decision |
|---|----------|
| Q1 | (b) HackSoft adapted for HTMX. No DRF / no `apis.py`. |
| Q2 | (a) Forms = I/O. Services own all business logic. (See [ADR-0002](./adr/0002-services-selectors-forms-as-io.md)) |
| Q3 | (a) Sequence: shared infra → users → properties → chat. |
| Q4a | `BaseModel` in `apps/shared/models.py` (`created_at`, `updated_at`, abstract). Skip for `User` (AbstractUser) and `Message` (immutable). Apply to `Conversation`, `Property`, `PropertyImage`, `Favorite`. |
| Q4b | Single `ApplicationError(Exception)` with `message: str` + optional `extra: dict`. Promote to a hierarchy when a real second-tier need appears. |
| Q4c | Plain `TestCase` + `factory_boy` dependency. No `pytest-django` migration. |
| Q4d | `apps/shared/{models,exceptions,services,validators}.py` + `tests/factories.py`. |
| Q5a | `users` view→layer mapping (signup→service, login/logout→thin, profile→selector, profile_edit→service, password_change→service, validate_email→selector). |
| Q5b | (iii) `CustomUserManager` kept as framework hook only. App code goes through `services.user_create`. (See [ADR-0003](./adr/0003-customusermanager-framework-hook-exception.md)) |
| Q5c | (ii) `validate_password_strength` moves to `apps/shared/validators.py`. |
| Q5d | `apps/users/` final layout includes `services.py`, `selectors.py`, `tests/{services,selectors,views}/`. |
| Q6a | Property validators (`validate_phone`, `validate_cnic`) move to `apps/shared/validators.py`. HTMX validation endpoints (`validate_phone_view`, `validate_cnic_view`) stay in `properties/views.py`. |
| Q6b | (i) Composite service: `property_create(*, owner, data, images)` — single transaction. Edit: `property_update(*, property, data, new_images=None, delete_image_ids=None)`. |
| Q6c | (ii) Multi-step wizard validation stays in form layer. Not a selector, not a service. |
| Q6d | `delete_property_and_assets` → `services.property_delete(*, property)` (drop `request` arg). `handle_document_download` splits: selector `property_document_get` returns file/path; view builds `FileResponse`. Delete `apps/properties/utils.py`. |
| Q7a | Rate limit splits: selector `message_rate_limit_status(*, user)` reads window state; service `message_rate_limit_consume(*, user)` performs atomic check-and-increment. Atomicity inside service (Redis pipeline). |
| Q7b | Three chat HTTP views map: `conversation_list` → selector `conversation_list_for_user`; `conversation_detail` → selector + selector + service `message_mark_read`; `start_conversation` → service `conversation_get_or_create`. `mark_read` on GET preserved (existing test expects it). |
| Q7c | Tests relocated, NOT rewritten. Existing `TransactionTestCase` classes split by responsibility into `chat/tests/{consumers,services,selectors,views,admin}/`. New service/selector tests added as new code lands. |
| Q7d | `apps/chat/` final layout: thin `consumers.py`, plus `services.py`, `selectors.py`, 3-view `views.py`, `tests/` package. |
| Q8a | 7 PRs (#0 through #6). |
| Q8b | All 5 gates per PR: `manage.py check`, `makemigrations --check --dry-run`, `manage.py test`, `ruff check`, `ruff format --check`. New service/selector ships with at least one test in same PR. |
| Q8c | `CONTEXT.md` born at PR #1. |
| Q8d / Q9 | (ii) Settings split per integration. Rename `development.py` → `local.py`. PR #0. (See [ADR-0004](./adr/0004-settings-split-per-integration.md)) |

## PR sequence

### PR #0 — settings split

Goal: pure mechanical reshape of `config/`. No behavior change. Independent risk surface from layering work.

- Create `config/django/{base,local,production}.py` (move existing `base.py`, `production.py`; rename `development.py` → `local.py`).
- Create `config/settings/{storages,channels,axes,unfold,whitenoise}.py`. Extract integration-specific blocks from old `base.py` into these files.
- Add `from config.settings.<integration> import *` lines at top of `config/django/base.py`.
- Update `DJANGO_SETTINGS_MODULE` references:
  - `manage.py`
  - `config/wsgi.py`
  - `config/asgi.py`
  - `Dockerfile` (any `ENV DJANGO_SETTINGS_MODULE=` line)
  - `docker-compose.yml`
  - `.env.dev`, `.env.prod`, `.env.sample`
  - `justfile`, `scripts/` if applicable
  - `.github/workflows/`
  - `pyproject.toml` (`[tool.ruff]` excludes if any reference settings paths)
- Smoke-test: `python manage.py check` + `just runserver` + `docker compose up` + run existing tests.

### PR #1 — shared infrastructure + docs + ADRs

- Create `apps/shared/`:
  - `models.py` — `class BaseModel(models.Model)` abstract with `created_at` (db_index=True) + `updated_at`.
  - `exceptions.py` — `class ApplicationError(Exception)` with `message: str`, optional `extra: dict`.
  - `validators.py` — moved `validate_phone`, `validate_cnic` from `properties/validations.py`; moved `validate_password_strength` from `users/forms.py`.
  - `tests/__init__.py`, `tests/factories.py` — base mixins (empty for now).
- `INSTALLED_APPS`: `apps.shared` already registered (`apps/shared/apps.py` exists).
- Add `factory_boy` to `dev` dependencies in `pyproject.toml`. Run `uv lock`.
- Create `CONTEXT.md` at repo root.
- Create `docs/adr/0001..0004.md`.
- No app touched. Net-add only. Migrations: none (BaseModel is abstract).

### PR #2 — users refactor

- Create `apps/users/services.py`: `user_create`, `user_update`, `user_change_password`.
- Create `apps/users/selectors.py`: `user_get`, `user_email_exists`.
- Refactor `apps/users/views.py` — each view becomes thin (form → service/selector → render).
  - `signup_view` → `services.user_create`
  - `login_view`, `logout_view` → unchanged (use Django auth directly)
  - `profile_view` → `selectors.user_get`
  - `profile_edit_view` → `services.user_update`
  - `password_change_view` → `services.user_change_password`
  - `validate_email_view` → `selectors.user_email_exists`
- `apps/users/forms.py`:
  - Remove `validate_password_strength` (moved in PR #1, import from `apps.shared.validators`).
  - Forms validate field shape only; remove any business-rule logic.
- Convert `apps/users/tests.py` (if any) to `apps/users/tests/` package:
  - `factories.py` — `UserFactory`.
  - `services/test_user_create.py`, `test_user_update.py`, `test_user_change_password.py`.
  - `selectors/test_user_get.py`, `test_user_email_exists.py`.
  - `views/test_signup.py`, `test_login.py`, `test_profile.py`, `test_password_change.py`.
- `User` model unchanged (uses AbstractUser timestamps; CustomUserManager kept per ADR-0003).
- No migrations.

### PR #3 — properties refactor

- Create `apps/properties/services.py`:
  - `property_create(*, owner, data, images)` — composite, transactional.
  - `property_update(*, property, data, new_images=None, delete_image_ids=None)`.
  - `property_delete(*, property)` — replaces `delete_property_and_assets`, drops `request` arg.
  - `property_favorite_toggle(*, user, property)`.
- Create `apps/properties/selectors.py`:
  - `property_list(*, filters=None, owner=None)` (covers `properties_list_view`, `my_properties_list_view`).
  - `property_get(*, property_id)`.
  - `property_favorites_for_user(*, user)`.
  - `property_document_get(*, property)` — returns file path/URL for download view.
- Refactor `apps/properties/views.py` — each view thin:
  - `properties_list_view`, `my_properties_list_view`, `favorites_list_view`, `property_detail_view` → selectors.
  - `property_create_view`, `property_edit_view` → services.
  - `property_delete_view` → service.
  - `property_favorite_toggle_view` → service.
  - `property_download_document_view` → selector + view-built `FileResponse`.
  - `property_validate_step_view`, `validate_phone_view`, `validate_cnic_view` → form / shared validators.
- Delete `apps/properties/utils.py`.
- Delete `apps/properties/validations.py` (moved to `apps/shared/validators.py` in PR #1).
- `apps/properties/forms.py`: forms validate shape only. `PropertyForm.save()` removed if present; service handles persistence.
- Migrations:
  - `Property` adopts `BaseModel` → adds `updated_at` (default `now()`).
  - `PropertyImage` adopts `BaseModel` → adds `created_at`, `updated_at`.
  - `Favorite` adopts `BaseModel` → adds `created_at`, `updated_at`.
- Tests reorganized into `apps/properties/tests/{services,selectors,views,factories.py}`.

### PR #4 — chat refactor (consumer + views)

- Create `apps/chat/services.py`:
  - `message_create(*, conversation, sender, content)`.
  - `message_mark_read(*, conversation, reader)`.
  - `conversation_get_or_create(*, property, initiator)`.
  - `message_rate_limit_consume(*, user)` — atomic Redis check-and-increment.
- Create `apps/chat/selectors.py`:
  - `conversation_get(*, conversation_id, user)` — also enforces participant.
  - `conversation_list_for_user(*, user)`.
  - `conversation_get_recipient(*, conversation, user)`.
  - `message_list_for_conversation(*, conversation)`.
  - `message_rate_limit_status(*, user)`.
- Refactor `apps/chat/consumers.py`:
  - Remove `check_user_is_participant`, `get_conversation`, `get_recipient_id`, `save_message`, `check_rate_limit`.
  - Wrap service/selector calls in `database_sync_to_async`.
  - Keep transport-only methods: `connect`, `disconnect`, `receive`, `_dispatch`, `_send_error`, `chat_message`.
- Refactor `apps/chat/views.py`:
  - `conversation_list` → selector.
  - `conversation_detail` → selector + selector + service `message_mark_read` (preserves existing GET-side-effect behavior; tests depend on this).
  - `start_conversation` → service `conversation_get_or_create`.
- Migrations:
  - `Conversation` adopts `BaseModel` (already has both timestamps; no schema change).
  - `Message` keeps own `created_at`, no `updated_at` added.
- New service/selector tests added; existing tests stay in `tests.py` for this PR (split happens in PR #5).

### PR #5 — chat tests split

Pure mechanical relocation of `apps/chat/tests.py` (2502 lines, 7 `TransactionTestCase` classes) into:

```
apps/chat/tests/
├── __init__.py
├── factories.py                    # ConversationFactory, MessageFactory, UserFactory re-export
├── consumers/
│   └── test_chat_consumer.py       # ChatConsumerTestCase + RateLimitingTestCase + OfflineMessageHandlingTestCase
├── services/
│   ├── test_message_create.py
│   ├── test_message_mark_read.py
│   ├── test_conversation_get_or_create.py
│   └── test_message_rate_limit.py
├── selectors/
│   ├── test_conversation_get.py
│   ├── test_conversation_list_for_user.py
│   └── test_message_list_for_conversation.py
├── views/
│   ├── test_conversation_list.py   # ConversationListViewTestCase
│   ├── test_conversation_detail.py # ConversationDetailViewTestCase
│   └── test_start_conversation.py  # StartConversationViewTestCase
└── admin/
    └── test_conversation_admin.py  # ConversationAdminTestCase
```

No test bodies rewritten. New service-level tests added in PR #4 already.

### PR #6 — documentation refresh

- Update `AGENTS.md`: replace "Each app follows Django's standard structure" section with services/selectors/forms-as-IO conventions. Reference ADRs 0001–0004.
- Update `docs/architecture/overview.md`: add layered architecture diagram (View → Service → Model). Document `apps/shared/`.
- Update `CONTRIBUTING.md` if it documents file conventions.
- Add `docs/development/services-and-selectors.md` — short how-to for new contributors writing their first service.

## Quality gates (every PR)

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- `ruff check`
- `ruff format --check`
- Pre-commit hooks pass (`.pre-commit-config.yaml` already configured).

## New conventions enforced

- Services take **keyword-only args** (`def user_create(*, email, password, ...)`). Exception: services with a single, obvious positional arg.
- Services and selectors include **type annotations** on all parameters and return types.
- Services name pattern: `<entity>_<action>` — `user_create`, `property_update`.
- Selectors name pattern: `<entity>_<query>` — `user_get`, `conversation_list_for_user`.
- Services call `instance.full_clean()` before `instance.save()` when constructing models manually.
- No business logic in `Model.save()`, `Form.save()`, signals, or custom managers (CustomUserManager exception per ADR-0003).
- Views and consumers contain no ORM access — always go through a service or selector.
- Forms call only field-shape validators (regex, type, format). No DB lookups, no cross-field business rules.

## Out of scope (deferred)

- DRF / public REST API.
- Celery (no celery installed).
- Switching test runner to pytest.
- `ApplicationError` hierarchy beyond the base class.
- `config/django/test.py` — added when test settings first need to diverge from `local.py`.
