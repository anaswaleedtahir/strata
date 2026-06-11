# Deployment Checklist

## Pre-Deployment

### Frontend Build
- [ ] Run `uv run python manage.py tailwind build --force` to compile Tailwind CSS
- [ ] Verify `static/dist/output.css` exists and is up-to-date

### Static Files
- [ ] Run `python manage.py collectstatic --noinput`
- [ ] Verify no errors about missing files
- [ ] Check `staticfiles/dist/` contains hashed CSS files
- [ ] Confirm `assets/css/input.css` is not collected as a static file

### Environment Variables
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with production domains
- [ ] Set secure `SECRET_KEY` (use secrets manager)
- [ ] Configure `DATABASE_URL` for production database
- [ ] Set AWS credentials if using S3
- [ ] Configure `DJANGO_SETTINGS_MODULE=config.settings.production`

### Security
- [ ] Enable HTTPS/SSL
- [ ] Configure CSRF trusted origins
- [ ] Set secure cookie flags
- [ ] Configure CORS if needed
- [ ] Review security middleware settings

## Docker Build

### Build Arguments
```bash
docker build \
  --build-arg SECRET_KEY=dummy-build-only-key \
  --build-arg DATABASE_URL=sqlite:///tmp/build.db \
  --build-arg DEBUG=False \
  --build-arg ALLOWED_HOSTS=localhost \
  -t property-hub:latest .
```

### Build Verification
- [ ] Build completes without errors
- [ ] No "missing file" errors during collectstatic
- [ ] Image size is reasonable (check with `docker images`)
- [ ] Runtime image doesn't contain a Node.js toolchain
- [ ] Runtime image contains `staticfiles/` directory

### Test Container
```bash
docker run -p 8000:8000 \
  -e SECRET_KEY=test-key \
  -e DATABASE_URL=sqlite:///db.sqlite3 \
  -e DEBUG=False \
  -e ALLOWED_HOSTS=localhost \
  property-hub:latest
```

- [ ] Container starts successfully
- [ ] Health check passes
- [ ] Static files are served correctly
- [ ] CSS loads and styles are applied
- [ ] No 404 errors for static files

## Post-Deployment

### Monitoring
- [ ] Set up application monitoring
- [ ] Configure error tracking (Sentry, etc.)
- [ ] Set up log aggregation
- [ ] Configure uptime monitoring
- [ ] Set up performance monitoring

### Verification
- [ ] Test all major user flows
- [ ] Verify static files load correctly
- [ ] Check CSS and JavaScript functionality
- [ ] Test file uploads (if applicable)
- [ ] Verify database connections
- [ ] Test WebSocket connections (chat)

### Performance
- [ ] Verify static files are compressed (gzip)
- [ ] Check cache headers are set correctly
- [ ] Test page load times
- [ ] Verify CDN is working (if applicable)

## Rollback Plan

### Quick Rollback
```bash
# Revert to previous image
docker pull property-hub:previous-tag
docker-compose up -d

# Or use orchestration rollback
kubectl rollout undo deployment/property-hub
```

### Database Rollback
- [ ] Have database backup ready
- [ ] Test restore procedure
- [ ] Document migration rollback steps

## Common Issues

### Static Files Not Loading
1. Check `STATIC_URL` and `STATIC_ROOT` settings
2. Verify `collectstatic` ran successfully
3. Check WhiteNoise middleware is enabled
4. Verify file permissions in container

### CSS Not Applied
1. Check browser console for 404 errors
2. Verify `output.css` exists in `staticfiles/dist/`
3. Check template loads correct CSS path
4. Clear browser cache

### Build Fails at collectstatic
1. Ensure `uv run python manage.py tailwind build --force` ran first
2. Check `assets/css/input.css` exists in build context
3. Verify `static/dist/output.css` was created
4. Check no source files in `static/` directory

### Container Won't Start
1. Check environment variables are set
2. Verify database is accessible
3. Check logs: `docker logs <container-id>`
4. Verify health check endpoint works

## Environment-Specific Notes

### Development
- Use `config.settings.development`
- `DEBUG=True` is acceptable
- Can use SQLite for database
- Static files served by Django

### Staging
- Use `config.settings.production`
- `DEBUG=False`
- Use production-like database
- Test full deployment process

### Production
- Use `config.settings.production`
- `DEBUG=False` (critical!)
- Use managed database service
- Enable all security features
- Use secrets manager for credentials
- Enable monitoring and logging

## Automation

### CI/CD Pipeline
```yaml
# Example GitHub Actions workflow
- name: Build Frontend
  run: uv run python manage.py tailwind build --force

- name: Collect Static Files
  run: python manage.py collectstatic --noinput

- name: Build Docker Image
  run: docker build -t property-hub:${{ github.sha }} .

- name: Run Tests
  run: docker run property-hub:${{ github.sha }} pytest

- name: Push to Registry
  run: docker push property-hub:${{ github.sha }}
```

### Recommended Tools
- **CI/CD**: GitHub Actions, GitLab CI, CircleCI
- **Container Registry**: Docker Hub, AWS ECR, Google GCR
- **Orchestration**: Docker Compose, Kubernetes, AWS ECS
- **Monitoring**: Datadog, New Relic, Prometheus
- **Error Tracking**: Sentry, Rollbar
- **Secrets**: AWS Secrets Manager, HashiCorp Vault

## Support

### Documentation
- [Frontend Architecture](./FRONTEND_ARCHITECTURE.md)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [WhiteNoise Documentation](http://whitenoise.evans.io/)

### Getting Help
- Check application logs
- Review Django debug toolbar (development only)
- Consult team documentation
- Review recent changes in git history
