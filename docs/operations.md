# Operations

## Install

Copy `.env.example` to `.env`, replace `SECRET_KEY` and `ADMIN_TOKEN` with long random values, then choose a database mode.

SQLite (single-instance, lightweight):

```bash
docker compose up -d --build
```

Bundled PostgreSQL (recommended) or MySQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build
```

For an external database, set `DATABASE_URL` to a `postgresql+asyncpg://` or `mysql+asyncmy://` URL and use the base command. URL-encode database credentials containing reserved characters.

The web interface is available at `http://localhost:3000`; API readiness is at `http://localhost:8000/health/ready`.

For a TLS deployment, set `APP_URL`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`, and `COOKIE_SECURE=true`, then place both services behind a TLS reverse proxy. Never expose a database port publicly.

## Upgrade

1. Back up the database.
2. Pull the new source or image tag.
3. Run `docker compose build --pull`.
4. Run `docker compose up -d`. The API runs forward migrations before accepting traffic.
5. Verify `/health/ready` and the public creation flow.

## Backup and restore

For SQLite, back up the `teamnav-sqlite` volume while the API is stopped. For bundled PostgreSQL, create a compressed backup:

```bash
docker compose exec -T postgres pg_dump -U teamnav -d teamnav -Fc > teamnav.dump
```

Restore into an empty database:

```bash
docker compose exec -T postgres pg_restore -U teamnav -d teamnav --clean --if-exists < teamnav.dump
```

For MySQL, use `mysqldump` and restore into an empty `teamnav` database. Always use the same Compose file combination for operational commands as for startup.

Backups contain password and capability-key hashes. Encrypt backup files, restrict access, and test restores regularly. Individual site JSON exports intentionally exclude all secrets and can be downloaded from the management page.

## Recovery and rotation

The recovery file generated during site creation contains the only recoverable copy of the edit key. Store it in a password manager. Operators cannot reconstruct edit keys from the database. If a key leaks, use the management page to rotate it; all existing management sessions are revoked.
