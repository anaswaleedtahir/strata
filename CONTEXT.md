# RealmKey

Server-rendered Django + HTMX real-estate platform. Property listings, owner profiles, real-time chat between buyers and owners. No public REST API; all interaction is through HTML responses and WebSocket events.

## Language

### Domain

**Property**:
A real-estate listing record (attributes, images, documents) owned by exactly one User.
_Avoid_: Listing, ad, post

**Owner**:
The User who created a Property. Authoritative term for the seller-side actor.
_Avoid_: Lister, seller, agent

**Favorite**:
A User-to-Property association recording interest. One per (User, Property) pair.
_Avoid_: Bookmark, like, save

**Conversation**:
A 1:1 thread between two Users about exactly one Property. Unique on (participant_one, participant_two, property).
_Avoid_: Thread, chat, room

**Participant**:
A User in a Conversation. A Conversation has exactly two Participants.
_Avoid_: Member, user

**Message**:
An immutable text payload posted by one Participant in a Conversation. Has a per-recipient read state. Never edited.
_Avoid_: Post, comment, reply

### Architecture

**Service**:
A function that writes to the database or otherwise mutates state. Named `<entity>_<action>` (e.g. `property_create`, `message_create`). Takes keyword-only args. Raises `ApplicationError` on business-rule violation.

**Selector**:
A function that reads from the database. Named `<entity>_<query>` (e.g. `conversation_list_for_user`, `user_email_exists`). Returns querysets, lists, or scalars. Never mutates.

**Form**:
An I/O adapter (HTML POST ⇄ Python dict). Validates field shape and format only. Never contains business logic. Never calls `.save()` on a model when a service exists for that entity.

**View**:
HTTP request handler. Three lines: parse via Form, call Service or Selector, render template. No ORM access; no business logic.

**Consumer**:
WebSocket transport (Django Channels). Same rule as View — delegates DB work to Services and Selectors via `database_sync_to_async`.

**ApplicationError**:
Domain exception raised by Services. Has `message: str` and optional `extra: dict`. Caught by Views and Consumers; mapped to form errors or WebSocket error events.

**BaseModel**:
Abstract model in `apps/shared/models.py` providing `created_at` + `updated_at`. Adopted by models that mutate over time. Skipped by `User` (uses `AbstractUser` timestamps) and `Message` (immutable).

### Presentation

**Shell template**:
A project-root layout under `templates/_layouts/` (`base.html`, `auth.html`, `dashboard.html`). Owns global UI structure, theme attribute, HTMX/Alpine setup, and navigation. App pages extend a shell; HTMX partials do not.
_Avoid_: Putting domain markup in shell templates

**App template**:
A page or fragment owned by one Django app, under `apps/<app>/templates/<app>/`. Full pages at the app root; HTMX fragments in `partials/`; reusable domain widgets in `components/`.
_Avoid_: Putting app pages in project-root `templates/<app>/`

**Field primitive**:
The single reusable form control at `templates/_components/forms/field.html`. Renders any bound form field via `widget_tweaks` (`render_field`). App form partials compose fields; they do not hand-build `<input>` markup.
_Avoid_: `input.html`, per-type field templates, scattering `add_class` across pages

**Form partial**:
An app-scoped template that lays out fields for one form (e.g. `login_form.html`). Returned as an HTMX fragment or included by a full page. Lives with its app domain, not in the design-system layer.
_Avoid_: Calling full-page templates "partials"

**HTMX partial**:
A template fragment returned when `request.htmx` is true. No `extends`; swapped into an existing DOM target. Colocated with the owning app under `apps/<app>/templates/<app>/partials/`.
_Avoid_: Extending `base.html` in a partial, putting partials in root `_components/<app>/`

## Relationships

- A **User** owns zero or more **Properties**
- A **Property** has zero or more **PropertyImages** and zero or more **Favorites**
- A **Favorite** belongs to exactly one **User** and one **Property**
- A **Conversation** has exactly two **Participants** (Users) and references exactly one **Property**
- A **Conversation** contains zero or more **Messages**
- A **Message** has exactly one sender (Participant) and one read state per recipient

## Layer rules

- **View** → calls **Form** → calls **Service** or **Selector** → returns template
- **Consumer** → calls **Service** or **Selector** (wrapped in `database_sync_to_async`)
- **Service** → may call other Services or Selectors; may raise **ApplicationError**
- **Selector** → may call other Selectors; never mutates
- **Form** → may call shared validators; never calls Service or Selector
- **Model** → no business logic in `save()`; constraints at DB level; properties for trivial derived values

## Example dialogue

> **Dev:** "Where does the rate-limit check for sending a **Message** live?"
> **Architect:** "Two layers. A **Selector** `message_rate_limit_status` reads the current window, useful for UI hints. A **Service** `message_rate_limit_consume` performs the atomic check-and-increment when a Message is actually being sent. The **Consumer** calls the Service inside `database_sync_to_async` and rejects via WebSocket error event if not consumed."

> **Dev:** "When a User signs up, the **Form** validates the email format. Where does the uniqueness check go?"
> **Architect:** "Format goes in the Form. Uniqueness is a business rule — Service. `user_create` raises `ApplicationError('email already taken')`. The View catches it and calls `form.add_error('email', e.message)`."
