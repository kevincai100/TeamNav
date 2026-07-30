# Operations

## Install

Copy `.env.example` to `.env`, replace `SECRET_KEY` and `ADMIN_TOKEN` with long random values, then choose a database mode. Published images default to the public `glfc2b/teamnav-*` Docker Hub repositories. Bundled database passwords are interpolated into `DATABASE_URL`, so restrict them to URL-safe characters such as letters, digits, `.`, `_`, `~`, and `-`.

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
docker compose pull
docker compose up -d --no-build
```

Bundled PostgreSQL (recommended) or MySQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml pull
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --no-build
docker compose -f docker-compose.yml -f docker-compose.mysql.yml pull
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --no-build
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

Create a host backup directory first. Keep it outside source control and copy encrypted backups to
another machine or object store.

```bash
mkdir -p backups
```

Native database backups restore into the same database engine. They are not a cross-engine migration
format. Always create a fresh backup immediately before a restore.

### SQLite

SQLite backups are copied while the application process is stopped, so the database file and any
journal state are consistent. For AIO SQLite:

```bash
docker compose -f docker-compose.aio.yml stop teamnav
docker compose -f docker-compose.aio.yml cp teamnav:/data/teamnav.db ./backups/teamnav-aio.db
docker compose -f docker-compose.aio.yml start teamnav
```

For split SQLite, replace the service and output name:

```bash
docker compose stop api
docker compose cp api:/data/teamnav.db ./backups/teamnav-sqlite.db
docker compose start api
```

To restore AIO SQLite, stop the application, copy the file into the data volume, repair ownership,
run SQLite's integrity check, and then wait for the migrated application to become healthy:

```bash
docker compose -f docker-compose.aio.yml stop teamnav
docker compose -f docker-compose.aio.yml cp ./backups/teamnav-aio.db teamnav:/data/teamnav.db
docker compose -f docker-compose.aio.yml run --rm --no-deps --user root --entrypoint chown teamnav teamnav:teamnav /data/teamnav.db
docker compose -f docker-compose.aio.yml run --rm --no-deps --entrypoint python teamnav -c "import sqlite3; db=sqlite3.connect('/data/teamnav.db'); result=db.execute('PRAGMA integrity_check').fetchone()[0]; assert result == 'ok', result"
docker compose -f docker-compose.aio.yml up -d --wait
```

For split SQLite, use the same sequence with the base Compose file and the `api` service instead of
`teamnav`.

### PostgreSQL

Create a compressed PostgreSQL backup inside the database container, copy it out, and remove the
temporary container copy:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres sh -ceu 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/teamnav.dump'
docker compose -f docker-compose.yml -f docker-compose.postgres.yml cp postgres:/tmp/teamnav.dump ./backups/teamnav-postgres.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres rm -f /tmp/teamnav.dump
```

Restore after stopping the API. `pg_restore --list` rejects a malformed archive before database
objects are changed:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml stop api
docker compose -f docker-compose.yml -f docker-compose.postgres.yml cp ./backups/teamnav-postgres.dump postgres:/tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres pg_restore --list /tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres sh -ceu 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction /tmp/teamnav.dump'
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T postgres rm -f /tmp/teamnav.dump
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --wait
```

### MySQL

Create a transactionally consistent MySQL SQL dump:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql sh -ceu 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u "$MYSQL_USER" --single-transaction --quick --routines --triggers --hex-blob --no-tablespaces "$MYSQL_DATABASE" > /tmp/teamnav.sql'
docker compose -f docker-compose.yml -f docker-compose.mysql.yml cp mysql:/tmp/teamnav.sql ./backups/teamnav-mysql.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql rm -f /tmp/teamnav.sql
```

Restore into a newly created `teamnav` database while the API is stopped:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml stop api
docker compose -f docker-compose.yml -f docker-compose.mysql.yml cp ./backups/teamnav-mysql.sql mysql:/tmp/teamnav.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql sh -ceu 'test -s /tmp/teamnav.sql; MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -e "DROP DATABASE IF EXISTS teamnav; CREATE DATABASE teamnav CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"; MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root teamnav < /tmp/teamnav.sql'
docker compose -f docker-compose.yml -f docker-compose.mysql.yml exec -T mysql rm -f /tmp/teamnav.sql
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --wait
```

Backups contain password and capability-key hashes. Encrypt backup files, restrict access, and test restores regularly. Individual site JSON exports intentionally exclude all secrets and can be downloaded from the management page.

## Recovery and rotation

The recovery file generated during site creation contains the only recoverable copy of the edit key. Store it in a password manager. Operators cannot reconstruct edit keys from the database. If a key leaks, use the management page to rotate it; all existing management sessions are revoked.
