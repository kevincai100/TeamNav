# TeamNav architecture

TeamNav is a monorepo with two deployable applications and a shared JSON template catalogue.

```text
Browser -> Next.js web -> FastAPI -> PostgreSQL
```

## Module seams

- The web module owns browser interaction, local search, creation and management views. It never decides whether a caller is authorized.
- The HTTP module adapts requests to the domain module and maps domain errors to stable error codes.
- The site domain module owns anonymous creation, capability keys, sessions, limits, imports and destructive operations.
- The persistence module owns SQLAlchemy models and transactions. PostgreSQL is used in deployment and SQLite is an adapter for tests and lightweight local development.
- Built-in templates are versioned JSON data. Applying a template is handled by the site domain module so clients cannot smuggle arbitrary persisted fields.

The capability key is returned only during creation or rotation. Only its SHA-256 digest is persisted. Browser management uses a separate random session token stored as an HttpOnly cookie; its digest is persisted and can be revoked without retaining the token.

## Deployment

The web and API containers are independently replaceable. Database state lives in a named Postgres volume. Caddy is intentionally omitted from the minimum compose file so operators can place TeamNav behind their existing TLS reverse proxy.
