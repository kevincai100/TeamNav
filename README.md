# TeamNav

TeamNav is an anonymous, shareable navigation homepage for teams. Creating a site produces a read-only public link and a separate unguessable management link. No account is required.

## Features

- Anonymous site creation with seven built-in templates, light/dark themes and optional access passwords
- Separate public and management capability links, QR sharing and downloadable recovery files
- Responsive public navigation with local search, category filters, pinned links and copy actions
- HttpOnly management sessions with CSRF protection
- Site, category and link editing, ordering, batch link creation and live preview
- Edit-key rotation, JSON import/export, confirmed deletion and abuse reporting
- Database-backed IP rate limiting, protocol allowlisting and secure default `noindex`
- PostgreSQL deployment with Alembic migrations and Docker Compose

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

Create `.env` from `.env.example`, set unique values for `SECRET_KEY` and `POSTGRES_PASSWORD`, then run:

```bash
docker compose up -d --build
```

For internet deployments, use TLS, set the public URLs and CORS origin, and set `COOKIE_SECURE=true`. Detailed upgrade, backup and restore steps are in [operations](docs/operations.md).

## Verification

```bash
npm run lint
npm run typecheck
npm test
npm run build

cd apps/api
../../.venv/Scripts/python -m pytest -q
../../.venv/Scripts/ruff check app tests alembic
```

## MVP scope notes

The core anonymous create, share, maintain, protect, report, import/export and self-host flows are implemented. Account login, organizations, simultaneous editing, SSO, subscriptions, custom domains, automatic favicon fetching and a cloud-operator admin console remain intentionally outside this anonymous MVP.
