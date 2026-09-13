# PR sandboxes

The PR Sandbox workflow deploys one API per same-repository PR to the separate
`infraspend-previews` Railway project. Each push updates that environment, waits
for `/health` to report the exact commit and sandbox mode, and then builds Pages
with the resulting API URL. The frontend is published at
`https://pr-<number>.infraspend.pages.dev`.

## One-time configuration

GitHub Actions secrets:

- `RAILWAY_API_TOKEN`: Railway workspace API token with access to the preview project.
  A production environment project token cannot manage these environments.
- `CLOUDFLARE_API_TOKEN`: Account / Cloudflare Pages / Edit, scoped to account
  `8b7b9d0fe58df1b2cec5b520ff92110c`.

Railway template already provisioned:

- Project: `50f0bb69-50f9-49cd-9b65-132436447fe6` (`infraspend-previews`).
- Base environment: `3361497b-88c2-4d0d-8908-85ccac0cd0ec` (Railway's default name
  `production`; this is an empty preview template, not the production API).
- Service: `api`, no source connected, no database service or volume.
- Dockerfile: `Dockerfile.preview`; upload `api` with `--path-as-root`.
- Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`.
- Healthcheck `/health`, one replica, sleeping enabled.
- Variables: `PREVIEW_SANDBOX=true`, `PORT=8000`, sandbox `AUTH0_DOMAIN` and
  `AUTH0_AUDIENCE`. No Infisical credentials.

Keep Railway's native PR environments disabled here: the GitHub workflow manages
creation and deletion itself, so it can coordinate both hosting providers.
Once the first paired deployment succeeds, disable automatic **preview** Git
builds in the existing Cloudflare Pages project. Keep production builds enabled.
Otherwise Cloudflare also creates independent previews with its old backend URL.

Merge the workflow into the default branch to make cleanup reliable for future
PRs. Fork PRs are intentionally skipped because they cannot receive deployment
credentials. The deployment script fails when a required secret is missing.

## Sandbox behavior

`PREVIEW_SANDBOX=true` explicitly selects a disposable SQLite file, regardless of
`DATABASE_URL`. SQLAlchemy creates the schema from the models; PostgreSQL SQL
migrations are not run in sandbox mode. The file lives under `/tmp`, with no
volume. Redeployment resets data; restarts may also discard it.

Auth0 JWT validation remains active. A new user's first login seeds twelve months
of sample AWS, Datadog and Heroku costs, account configurations and budgets, scoped
to that user. Budget edits use the real API/database. Provider credential writes
and scheduled ingestion are disabled; metrics reads serve sample rows without
calling providers. Preview application secrets come from environment variables,
with a random per-process session key. Infisical is not needed.

A banner identifies the sandbox. Its CORS regex accepts only HTTPS subdomains of
`infraspend.pages.dev`; production CORS behavior is unchanged. The Auth0 sandbox
application must retain its Pages callback, logout and web-origin allowlists.

Closing a PR deletes its Railway environment. Static Pages snapshots may remain,
but their API is gone. Do not use these snapshots as durable demos. SQLite previews
do not validate PostgreSQL migrations; retain database-specific CI tests.

## Local validation

From `api`, run `pytest`, `black --check .`, and `flake8`. The preview integration
test starts the real app in a subprocess with an isolated SQLite file and asserts
schema startup, sample reads, authentication requirements, credential-write blocking,
and CORS acceptance/rejection without Infisical.

To run manually, set `PREVIEW_SANDBOX=true`, `AUTH0_DOMAIN`, and `AUTH0_AUDIENCE`,
then run `uvicorn app.main:app --port 8000 --workers 1`. An optional
`PREVIEW_DB_PATH` selects a different disposable file.
