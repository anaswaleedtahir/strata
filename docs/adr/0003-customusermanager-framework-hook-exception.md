# `CustomUserManager` kept as a framework-hook exception

HackSoft says "avoid custom managers." We keep `apps/users/models.CustomUserManager` because Django's `createsuperuser` management command and the admin both invoke `User.objects.create_user(...)` / `create_superuser(...)`, and `AbstractUser` with `USERNAME_FIELD = "email"` (no username) **requires** overriding these methods to satisfy that contract.

## The rule

`CustomUserManager` exists **only** to satisfy framework hooks. **Application code never imports `User.objects.create_user` directly.** All app-level user creation, including django-allauth's adapter hook, goes through `apps.users.services.user_create(*, email, password, ...)`. The service may delegate to the manager internally; callers don't know.

## Why this is surprising

A future contributor reading HackSoft and then this codebase will see a custom manager and either (a) try to delete it (breaks `createsuperuser`) or (b) start calling it from views (defeats the whole layering decision in ADR-0002). This ADR is the answer to both impulses.
