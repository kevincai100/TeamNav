# Security model

- Edit keys and session tokens are generated from 32 bytes of cryptographic randomness and persisted only as keyed SHA-256 digests.
- Public access passwords use bcrypt. Changing a password invalidates previous public access sessions.
- Management mutations require an HttpOnly, SameSite cookie and a session-bound CSRF token.
- User links accept only `http`, `https`, `mailto`, and `tel`. The API does not fetch arbitrary favicons, avoiding an SSRF surface.
- Text fields are rendered as React text, never as user-provided HTML. External links use `noopener noreferrer`.
- Creation and reports store keyed IP digests rather than raw IP addresses.
- Public pages default to `noindex, nofollow`.

Production requires TLS, `COOKIE_SECURE=true`, a unique strong `SECRET_KEY`, trusted proxy configuration at the reverse proxy, rate limits appropriate to the deployment, log redaction for query strings, and routine dependency updates.

## Current dependency advisory

As of 2026-07-27, the latest stable Next.js release (`16.2.12`) pins PostCSS `8.4.31` and optionally installs Sharp `0.34.5`; npm reports high-severity advisories for both. TeamNav does not accept user CSS, source maps, or image uploads and does not use Next image optimization, so the vulnerable inputs are not exposed by the current product. Upgrade Next as soon as a compatible stable release moves to patched PostCSS (`8.5.18+`) and Sharp (`0.35.0+`). Do not follow npm's current automated suggestion to downgrade Next to `9.3.3`.
