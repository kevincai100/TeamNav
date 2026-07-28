# Operations

## Install

Copy `.env.example` to `.env`, replace `SECRET_KEY` and `ADMIN_TOKEN` with long random values, then choose a database mode.

All-in-one SQLite deployment (one application container):

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

The AIO image includes Nginx, Next.js, FastAPI and SQLite. It exposes only port `8080` inside the
container and stores the database under `/data` in the `teamnav-aio-data` volume. Set an external
`DATABASE_URL` to use PostgreSQL or MySQL with the same image.

To deploy published images instead of building from source:

```bash
docker compose pull
docker compose up -d --no-build
```

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

The web interface is available at `http://localhost:3000`; API readiness is proxied at
`http://localhost:3000/health/ready`. The API and web containers are not published directly.

For a TLS deployment, set `APP_URL` and `CORS_ORIGINS` to the public gateway origin, keep
`NEXT_PUBLIC_API_URL` empty, set `COOKIE_SECURE=true`, then place the gateway behind a TLS reverse
proxy. Never expose the API, web, or database container ports publicly.

## Upgrade

1. Back up the database.
2. Pull the new source or image tag.
3. For published images, run `docker compose pull`. For a source deployment, run `docker compose build --pull`.
4. Run `docker compose up -d`. The API runs forward migrations before accepting traffic.
5. Verify the gateway `/health/ready`, account session restoration and the public creation flow.

For the AIO deployment, the complete update command is:

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
docker compose -f docker-compose.aio.yml ps
```

The named data volume survives container replacement. The supervisor handles termination signals,
and database migrations run before the new container becomes healthy. Expect a short restart; use
the split deployment with multiple replicas and an external database when zero-downtime rollout is required.

## Backup and restore

For split SQLite, back up the `teamnav-sqlite` volume while the API is stopped. For AIO SQLite, stop
the container and copy the database before upgrading:

```bash
docker compose -f docker-compose.aio.yml stop teamnav
docker compose -f docker-compose.aio.yml cp teamnav:/data/teamnav.db ./teamnav.db
docker compose -f docker-compose.aio.yml start teamnav
```

For bundled PostgreSQL, create a compressed backup:

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
