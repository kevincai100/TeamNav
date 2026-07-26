# Operations

## Install

Copy `.env.example` to `.env`, replace `SECRET_KEY` with at least 32 random characters, set a strong `POSTGRES_PASSWORD`, then run:

```bash
docker compose up -d --build
docker compose ps
```

The web interface is available at `http://localhost:3000`; API readiness is at `http://localhost:8000/health/ready`.

For a TLS deployment, set `APP_URL`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`, and `COOKIE_SECURE=true`, then place both services behind a TLS reverse proxy. Never expose PostgreSQL publicly.

## Upgrade

1. Back up the database.
2. Pull the new source or image tag.
3. Run `docker compose build --pull`.
4. Run `docker compose up -d`. The API runs forward migrations before accepting traffic.
5. Verify `/health/ready` and the public creation flow.

## Backup and restore

Create a compressed backup:

```bash
docker compose exec -T postgres pg_dump -U teamnav -d teamnav -Fc > teamnav.dump
```

Restore into an empty database:

```bash
docker compose exec -T postgres pg_restore -U teamnav -d teamnav --clean --if-exists < teamnav.dump
```

Backups contain password and capability-key hashes. Encrypt backup files, restrict access, and test restores regularly. Individual site JSON exports intentionally exclude all secrets and can be downloaded from the management page.

## Recovery and rotation

The recovery file generated during site creation contains the only recoverable copy of the edit key. Store it in a password manager. Operators cannot reconstruct edit keys from the database. If a key leaks, use the management page to rotate it; all existing management sessions are revoked.
