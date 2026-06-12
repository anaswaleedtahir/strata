# Contributing to RealmKey

Thank you for your interest in contributing to RealmKey! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/realm-key.git
   cd realm-key
   ```
3. **Set up development environment**
   - Follow the [README.md](../README.md) setup instructions
   - Read the [Architecture Overview](./architecture/overview.md)

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add tests for new features
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests (SQLite — no local Postgres required)
DATABASE_URL=sqlite:///test.db python manage.py test

# Run a specific app
DATABASE_URL=sqlite:///test.db python manage.py test apps.properties

# Quality gates — run all before committing
DATABASE_URL=sqlite:///test.db python manage.py check
DATABASE_URL=sqlite:///test.db python manage.py makemigrations --check
uv run ruff check .
uv run ruff format --check .

# Test frontend build
uv run python manage.py tailwind build --force
python manage.py collectstatic --noinput --dry-run
```

### 4. Commit Your Changes

Follow the commit message format:

```
Type: Brief description (50 chars or less)

Detailed description if needed (wrap at 72 chars)

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

**Commit Types:**
- `Add:` - New features or files
- `Update:` - Changes to existing features
- `Fix:` - Bug fixes
- `Remove:` - Removing code or files
- `Refactor:` - Code restructuring
- `Docs:` - Documentation changes
- `Test:` - Test additions or updates
- `Chore:` - Maintenance tasks

**Examples:**
```bash
git commit -m "Add: User profile page with avatar upload"
git commit -m "Fix: Property search not filtering by price range"
git commit -m "Docs: Update deployment checklist with new steps"
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference to related issues
- Screenshots for UI changes
- Test results if applicable
- The exact repository PR template (auto-loaded by GitHub)

## Code Style Guidelines

### Python

This project follows the [HackSoftware Django Style Guide](https://github.com/HackSoftware/Django-Styleguide).

Core rules:
- **Services** (`services.py`) handle all writes; **selectors** (`selectors.py`) handle all reads
- Views are thin: validate form → call service/selector → render
- Forms validate I/O shape only — no DB queries, no `.save()`
- Services use keyword-only arguments and call `full_clean()` before saving
- Raise `ApplicationError` for domain violations, never `ValidationError` from services
- `ruff` enforces formatting; maximum line length 88 characters

**Service example:**
```python
# apps/properties/services.py
from apps.shared.exceptions import ApplicationError

def property_create(*, user, name: str, price: int) -> Property:
    if price <= 0:
        raise ApplicationError("Price must be positive.")
    prop = Property(user=user, name=name, price=price)
    prop.full_clean()
    prop.save()
    return prop
```

**Selector example:**
```python
# apps/properties/selectors.py
def property_list_published(*, user=None) -> QuerySet:
    return Property.published.all().select_related("user")
```

**Thin view example:**
```python
# apps/properties/views.py
@login_required
def property_create_view(request):
    form = PropertyForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        try:
            prop = property_create(user=request.user, **form.cleaned_data)
        except ApplicationError as e:
            form.add_error(None, e.message)
        else:
            return redirect("properties:detail", pk=prop.pk)
    return render(request, "properties/create.html", {"form": form})
```

### HTML/Templates

- Use semantic HTML5 elements
- Keep templates DRY with Cotton components for reusable UI
- Use Tailwind utility classes
- Add ARIA labels for accessibility
- Indent with 2 spaces

**Example:**
```html
{% extends "_layouts/base.html" %}

{% block content %}
<article class="max-w-4xl mx-auto p-6">
  <h1 class="text-3xl font-bold text-gray-900">
    {{ property.title }}
  </h1>

  <c-properties.property-card :property="property" />
</article>
{% endblock %}
```

### CSS

- Prefer Tailwind utilities over custom CSS
- Use `@layer components` for reusable components
- Use `@layer utilities` for custom utilities
- Keep custom CSS in `assets/css/input.css`
- Document complex custom styles

**Example:**
```css
@layer components {
  .property-card {
    @apply bg-white rounded-xl shadow-soft p-6;
    @apply transition-all duration-300;
    @apply hover:shadow-medium hover:-translate-y-1;
  }
}
```

### JavaScript

- Use modern ES6+ syntax
- Prefer Alpine.js for simple interactivity
- Use HTMX for dynamic content
- Add JSDoc comments for functions
- Keep JavaScript minimal

**Example:**
```javascript
/**
 * Initialize property search filters
 * @param {HTMLElement} container - The filter container element
 */
function initPropertyFilters(container) {
  // Implementation
}
```

## Testing Guidelines

### Writing Tests

- Test services and selectors directly — not through views
- Use `factory_boy` factories for test data; never inline raw `create_user()` in every test
- Use `django.test.TestCase` for sync tests; `TransactionTestCase` for async or WebSocket tests
- Split tests by layer: `test_services.py`, `test_views.py`, `test_consumers.py`, `test_admin.py`
- Test edge cases and error conditions (especially `ApplicationError` paths)

### Test Structure

```python
# apps/properties/tests/factories.py
import factory
from django.contrib.auth import get_user_model

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.django.Password("TestPass1!")
```

```python
# apps/properties/tests/test_services.py
from django.test import TestCase
from apps.properties.services import property_create
from apps.shared.exceptions import ApplicationError
from apps.shared.tests.factories import UserFactory

class PropertyCreateTest(TestCase):
    def test_creates_property(self):
        user = UserFactory()
        prop = property_create(user=user, name="Test", price=100000)
        self.assertEqual(prop.name, "Test")

    def test_raises_for_zero_price(self):
        user = UserFactory()
        with self.assertRaises(ApplicationError):
            property_create(user=user, name="Test", price=0)
```

## Documentation Guidelines

### When to Update Documentation

- Adding new features
- Changing architecture or design patterns
- Updating deployment processes
- Fixing bugs that affect documented behavior

### Documentation Standards

- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep it up-to-date with code changes
- Follow existing documentation structure

### Where to Add Documentation

- **Architecture changes**: `docs/architecture/`
- **Development guides**: `docs/development/`
- **Deployment updates**: `docs/deployment/`
- **How-to guides**: `docs/guides/`
- **API docs**: Inline docstrings + `docs/api/` (future)

## Pull Request Guidelines

> Every PR **must** use `.github/pull_request_template.md`.
> PRs that do not follow the template format or checklist will fail CI.

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow format
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Testing
Describe how you tested the changes

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Correct PR Example

Use this level of detail so reviewers can reproduce your changes quickly:

```markdown
## Description
Add validation for property area and improve error messages in property form.

## Type of Change
- [x] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #248

## Testing
- `uv run ruff check .`
- `uv run python manage.py check`
- `uv run python manage.py test apps.properties`

## Screenshots (if applicable)
N/A (no UI changes)

## Checklist
- [x] Code follows style guidelines
- [x] Tests added/updated
- [x] Documentation updated
- [x] No breaking changes (or documented)
```

### Screenshot Example for UI Changes

If your PR changes templates/styles/components, include screenshots:

```markdown
## Screenshots (if applicable)
### Before
![Before property detail page](https://user-images.githubusercontent.com/example/before.png)

### After
![After property detail page](https://user-images.githubusercontent.com/example/after.png)
```

### PR Compliance and Audit Process

All pull requests are audited for:

1. Required headings from the PR template
2. Presence of all checklist items
3. At least one checked checklist item (`- [x]`) to avoid blank submissions
4. Non-empty `## Description` and `## Testing` sections

This audit runs automatically in GitHub Actions as the `validate-pr-template` job on every pull request.

### Enforcing PR Templates in GitHub

Repository maintainers should verify these settings in GitHub:

1. Keep `.github/pull_request_template.md` in the default branch.
2. In **Settings → General → Pull Requests**, ensure contributors are prompted with templates (default behavior when template file exists).
3. In **Settings → Branches**, require status checks and mark `validate-pr-template` as required for protected branches.
4. Optionally add additional PR templates in `.github/PULL_REQUEST_TEMPLATE/` for special workflows.

With required checks enabled, non-compliant PR descriptions cannot be merged.

### Review Process

1. Automated checks must pass (linting, tests)
2. At least one approval required
3. Address review comments
4. Squash commits if requested
5. Maintainer will merge when ready

## Getting Help

### Resources

- [Documentation Index](./README.md)
- [Architecture Overview](./architecture/overview.md)
- [Development Guides](./development/)

### Communication

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Features**: Open a GitHub Issue with proposal
- **Security**: Email security@example.com (do not open public issue)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other unprofessional conduct

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- Project documentation (with permission)

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search closed issues and PRs
3. Open a GitHub Discussion
4. Ask in project communication channels

Thank you for contributing to RealmKey! 🎉
