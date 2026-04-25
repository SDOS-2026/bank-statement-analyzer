# FinParse Deployment Runbook

## Recommended production layout

- `frontend/` on Vercel
- `backend/` on Railway, Render, Fly.io, or any Java-capable host
- `python-service/` on Railway, Render, Fly.io, VM, or container host with `ghostscript`
- PostgreSQL on Neon, Supabase, Railway Postgres, Render Postgres, or managed Postgres

## Why not deploy the whole stack on Vercel?

The Angular frontend is a good Vercel fit.

The Java backend and the parser are not ideal Vercel targets for this app because:

- the backend is a long-lived Spring Boot service
- the parser depends on heavy document-processing tooling
- the parser uses local temp files during parsing
- `ghostscript` and PDF/table extraction are better suited to a container or VM environment

## Frontend on Vercel

Project root:

- set Vercel project root to `bankapp/frontend`

Environment variables:

- `NG_APP_API_URL=https://your-backend.example.com`

Project files already added:

- `frontend/vercel.json`
- `frontend/.env.example`
- `frontend/scripts/set-env.mjs`

Build output:

- Angular build output is `dist/frontend/browser`

## Backend environment variables

- `SPRING_DATASOURCE_URL`
- `SPRING_DATASOURCE_USERNAME`
- `SPRING_DATASOURCE_PASSWORD`
- `PARSER_SERVICE_URL`
- `CORS_ALLOWED_ORIGINS`
- `APP_JWT_SECRET`
- `APP_JWT_EXPIRATION_SECONDS`
- `APP_AUTH_ALLOW_PUBLIC_REGISTRATION`
- `APP_BOOTSTRAP_INTERNAL_EMAIL`
- `APP_BOOTSTRAP_INTERNAL_PASSWORD`
- `APP_BOOTSTRAP_INTERNAL_NAME`

Recommended values:

- `CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app`
- `APP_JWT_SECRET` should be a long random secret
- keep `APP_BOOTSTRAP_INTERNAL_*` only on the backend host, never in Vercel

## Parser service requirements

- Python 3
- packages from `requirements.txt`
- `ghostscript` installed on the host
- reachable by the backend through `PARSER_SERVICE_URL`

## Security model in production

- user registration creates `USER` accounts only
- internal dashboard access is limited to `INTERNAL` role
- statement APIs are owner-scoped unless an internal reviewer requests the all-statements scope
- CSV export is authenticated
- CORS is explicit, not wildcard
- password-protected files are retained only long enough to complete unlock parsing

## Important real-world flows now covered

- one user can upload multiple statements and see only their own list
- two users uploading files with the same filename no longer collide in parser temp storage
- password-unlock no longer depends on parser-local temp persistence across instances
- internal reviewers can see all statements without exposing them to normal users

## Deployment checklist

1. Provision PostgreSQL.
2. Deploy the parser service and confirm `/health`.
3. Deploy the backend with parser/database/auth env vars.
4. Create or confirm the internal reviewer bootstrap account.
5. Deploy the frontend to Vercel with `NG_APP_API_URL`.
6. Add the Vercel origin to `CORS_ALLOWED_ORIGINS`.
7. Verify:
   - user registration/login
   - upload and parse
   - password-protected upload
   - user cannot access another user’s statement URL
   - internal dashboard can see all statements
   - CSV export works while authenticated
