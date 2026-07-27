# TeamNav

TeamNav is a self-hosted, shareable navigation homepage for individuals and teams. Creating a site produces a public link and a separate unguessable management link. Accounts are optional and can synchronize multiple workspaces.

## Features

- Anonymous or account-based site creation with seven templates, light/dark themes and optional public access passwords
- Separate public and management capability links, QR sharing and downloadable recovery files
- Optional email accounts with workspace ownership, existing-site claiming and cross-device management
- Responsive public navigation with local search, category filters, favicons, click tracking and copy actions
- HttpOnly management sessions with CSRF protection
- Site, category and link editing, drag-and-drop ordering, optional batch tags and live preview
- Edit-key rotation, JSON/browser-bookmark import/export, cloning and basic daily statistics
- CAPTCHA, abuse reporting, admin report processing and site blocking
- SQLite, PostgreSQL or MySQL deployment with automatic Alembic migrations and Docker Compose

## Repository

- `apps/web`: Next.js 16, React 19 and TypeScript interface
- `apps/api`: FastAPI, SQLAlchemy 2 and Alembic
- `packages/templates`: versioned built-in templates
- `docs`: architecture, operations and security notes

See [architecture](docs/architecture.md), [operations](docs/operations.md), and [security](docs/security.md).

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

Lightweight SQLite, suitable for one application instance:

```bash
docker compose up -d --build
```

Bundled PostgreSQL, recommended for production:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
```

Bundled MySQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build
```

To use an external PostgreSQL or MySQL server, set `DATABASE_URL` in `.env` and use the lightweight base command; the SQLite volume remains mounted but is unused. Examples are provided in `.env.example`. Database tables are migrated automatically whenever the API container starts.

For internet deployments, use TLS, set the public URLs and CORS origin, and set `COOKIE_SECURE=true`. Detailed upgrade, backup and restore steps are in [operations](docs/operations.md).

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
