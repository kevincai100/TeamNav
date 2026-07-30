# TeamNav

[English](README.md) | [简体中文](README.zh-CN.md)

TeamNav is a self-hosted, shareable navigation homepage for individuals and teams. Creating a site produces a public link and a separate unguessable management link. Accounts are optional and can synchronize multiple workspaces.

## Features

- Anonymous or account-based site creation with seven templates, light/dark themes and optional public access passwords
- Separate public and management capability links, QR sharing and downloadable recovery files
- Optional email accounts with workspace ownership, existing-site claiming and cross-device management
- Responsive public navigation with local search, draggable category filters, favicons, click tracking and copy actions
- Workspace-level personalization for brand color, light/dark mode, canvas, card style, width, columns, density and content visibility
- HttpOnly management sessions with CSRF protection
- Site, category and link editing, collapsible folders, cross-folder drag-and-drop, optional batch tags and live preview
- Atomic JSON/browser-bookmark import/export with actionable capacity errors, cloning and basic daily statistics
- Automatic Chinese/English interface selection with a saved manual override
- Bookmark import preview with merge/replace, duplicate handling and capacity checks
- Link health checks, opt-in scheduled maintenance and recoverable change history
- CAPTCHA, abuse reporting, admin report processing and site blocking
- One-image SQLite deployment, or split SQLite, PostgreSQL and MySQL stacks with automatic migrations

## Repository

- `apps/web`: Next.js 16, React 19 and TypeScript interface
- `apps/api`: FastAPI, SQLAlchemy 2 and Alembic
- `packages/templates`: versioned built-in templates
- `docs`: architecture, operations and security notes

See [architecture](docs/architecture.md), [operations](docs/operations.md), and [security](docs/security.md).
The published images are also available on Docker Hub: [AIO](https://hub.docker.com/r/glfc2b/teamnav-aio),
[API](https://hub.docker.com/r/glfc2b/teamnav-api), and [web](https://hub.docker.com/r/glfc2b/teamnav-web).

## Local development

Requirements: Node.js 24+ and Python 3.12+.

```bash
npm install
npm run dev
```

In a second terminal:

```bash
python -m venv .venv
.venv/Scripts/pip install -e "apps/api[dev]" # Windows
cd apps/api
set DATABASE_URL=sqlite+aiosqlite:///./teamnav.db
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

On macOS/Linux, activate `.venv/bin/activate` and use `export DATABASE_URL=...`.

Open `http://localhost:3000`. The web app expects the API at `http://localhost:8000` by default; override `NEXT_PUBLIC_API_URL` before building when needed.

## Docker deployment

Create `.env` from `.env.example` and set unique values for `SECRET_KEY` and `ADMIN_TOKEN`.
The default Compose stack exposes a single gateway at `http://localhost:3000`; API requests stay
same-origin and are forwarded to the private API container.

### One-image deployment

For the simplest installation, run the published all-in-one image. It contains Nginx, the web app,
the API and SQLite, while application data remains in a named Docker volume:

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

The site is available at `http://localhost:3000`. Only one application container is created. To use
an external PostgreSQL or MySQL server, set `DATABASE_URL` before starting the same AIO stack.

Each workspace supports 200 folders and 2,000 bookmarks by default. Override
`MAX_CATEGORIES_PER_SITE` and `MAX_LINKS_PER_SITE` when a deployment needs different limits.
Automatic link checks are opt-in per workspace. Deployment-wide scheduling is controlled by
`LINK_CHECK_SCHEDULER_ENABLED`, `LINK_CHECK_POLL_SECONDS`, `LINK_CHECK_TIMEOUT_SECONDS` and
`LINK_CHECK_BATCH_SIZE`. Private and local network targets are blocked by default; only set
`LINK_CHECK_ALLOW_PRIVATE_NETWORKS=true` on a trusted private deployment.

The equivalent direct Docker command is:

```bash
docker volume create teamnav-data
docker run -d --name teamnav --restart unless-stopped \
  --env-file .env \
  -p 3000:8080 \
  -v teamnav-data:/data \
  glfc2b/teamnav-aio:latest
```

Update the AIO deployment without losing data:

```bash
docker compose -f docker-compose.aio.yml pull
docker compose -f docker-compose.aio.yml up -d
```

Docker recreates the application container and reuses the data volume. The entrypoint applies
forward database migrations before serving traffic and shuts all internal processes down cleanly.
This is a short restart, not a zero-downtime hot reload. Automatic updaters such as Watchtower are
optional and intentionally not enabled because they require Docker Socket access.

### Split deployment

Pull the published images without building locally:

```bash
docker compose pull
docker compose up -d --no-build
```

Lightweight split SQLite, suitable for one application instance:

```bash
docker compose pull
docker compose up -d --no-build
```

Bundled PostgreSQL, recommended for production:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml pull
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --no-build
```

Bundled MySQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml pull
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --no-build
```

To use an external PostgreSQL or MySQL server, set `DATABASE_URL` in `.env` and use the lightweight base command; the SQLite volume remains mounted but is unused. Examples are provided in `.env.example`. Database tables are migrated automatically whenever the API container starts.

### Build images from source

Clone the repository, create `.env` from `.env.example`, and build the all-in-one image locally:

```bash
git clone https://github.com/kevincai100/TeamNav.git
cd TeamNav
cp .env.example .env
docker compose -f docker-compose.aio.yml build --pull
docker compose -f docker-compose.aio.yml up -d
```

To build the split web and API images instead:

```bash
docker compose build --pull
docker compose up -d
```

Images built from `main` are published as both `main` and `latest`. Version tags such as `v0.1.0`
also publish immutable semantic-version tags. Production deployments can pin `TEAMNAV_VERSION` to a
specific version rather than following `latest`.

For internet deployments, use TLS, set `APP_URL` and `CORS_ORIGINS` to the public gateway origin,
and set `COOKIE_SECURE=true`. `NEXT_PUBLIC_API_URL` should remain empty for the portable same-origin
image. Detailed upgrade, backup and restore steps are in [operations](docs/operations.md).

Native backups restore into the same database engine. Cross-engine migration, such as SQLite to
PostgreSQL, is a separate data-migration operation rather than a database-file restore.

## Verification

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run e2e

cd apps/api
../../.venv/Scripts/python -m pytest -q
../../.venv/Scripts/ruff check app tests alembic
```

## MVP scope notes

The current MVP includes anonymous and account-based ownership, public sharing, management, protection, moderation, import/export, statistics and self-hosting. Organizations, simultaneous editing, SSO, subscriptions and custom domains remain outside scope.

## Contributing and security

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.
Please report vulnerabilities privately through GitHub Security Advisories as described in
[SECURITY.md](SECURITY.md), rather than in a public issue.
Every push and pull request is scanned for committed secrets before container images can be published.

## License and branding

TeamNav source code is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE).
If you run a modified version as a network service, the AGPL requires you to offer its corresponding
source code to the users of that service. The TeamNav name and branding are not granted under the
software license; see [TRADEMARKS.md](TRADEMARKS.md).

Copyright (C) 2026 TeamNav contributors.
