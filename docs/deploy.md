# Deploy Zelta for laptop and phone access

The code is prepared for a Supabase database/auth project, a Render Python API and a Vercel
Next.js frontend. These are three separate parts of one application. No service is created by
committing the deployment files. The owner has confirmed there are currently no Render/Vercel
accounts and Supabase has not yet been resumed.

## Resume Supabase first

Open https://supabase.com/dashboard, select Zelta and resume the project. Keep the existing
project/data. Wait until it is available before connecting the backend. Do not reset or delete it.
Use Supabase's Connect panel to obtain the PostgreSQL connection string suitable for your host;
use SSL and the pooler if direct connectivity is unavailable. Enter credentials only in service
environment settings. The public project URL and anon/publishable key are used by the frontend;
the database password and service-role key must never appear in `NEXT_PUBLIC_*` variables.
Migration 005 enables row-level security and removes direct anonymous/authenticated table access
for the nine Zelta-managed tables. Browsers must use FastAPI, which applies user ownership checks.
Use the trusted database owner connection for backend migrations and access; a restricted custom
database role requires an intentional privilege/policy design. This does not modify Supabase Auth
tables or unrelated application tables.

## Create the Render API

Create a Render account with GitHub and connect `sukruthhh/zelta-stockscreener`. Create a Blueprint
from the repository's `render.yaml`. It requests a free Docker web service and does not provision
a database or Redis. Confirm the dashboard's displayed plan and costs before creating anything.
Free hosting can sleep and is for the initial functional deployment, not guaranteed constant uptime.

Provide these values when prompted:

| Variable | Value |
| --- | --- |
| `POSTGRES_URL` | Existing Supabase PostgreSQL URL with SSL configured. Keep it secret. |
| `SUPABASE_URL` | Existing project URL, such as `https://project.supabase.co`. |
| `CORS_ORIGINS` | Initially `http://localhost:3000`; replace with the actual Vercel production origin once known. |

The Blueprint uses `backend/Dockerfile` and `/ready` for health checks. Startup applies existing
migrations. A running database and configured Supabase URL are required for readiness; this does
not prove that the URL, JWT signing configuration or delivered sign-in links work. `/health`
also shows optional Redis availability. Redis is unnecessary for the initial product workflow;
unavailable cache connections have two-second connect/read timeouts. Add hosted Redis later if
measured demand warrants it, without relying on local Redis from the owner's laptop.

Keep `NEWS_SENTIMENT_ENABLED=false` and `ENABLE_DIAGNOSTIC_ROUTES=false` for the initial release.
Analysis then uses price-based indicators without invoking news/embedding services. Missing-news
warnings are intentional. There is no need to supply Finnhub/OpenAI credentials for this mode.
Do not enable diagnostics publicly: the routes return 404 by default; when explicitly enabled
they also require authentication. No admin-role system is implemented, so enabling them permits
any authenticated user to reach those routes.

## Create the Vercel website

Create a Vercel account with GitHub and import the same repository. Set **Root Directory** to
`frontend`, select Next.js, and use `main` as the production branch. The committed `vercel.json`
selects the production webpack build already verified by CI. Set these build environment values:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | The same Supabase project URL used by the backend. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase's public anon/publishable key. Never the service-role key. |
| `NEXT_PUBLIC_API_URL` | The deployed Render HTTPS origin, without a trailing slash. |

These public variables are embedded during the frontend build. Redeploy after changing them.
The committed `frontend/.env.local.example` is only a local-development template, not credentials.

Copy the Vercel production origin to Render's `CORS_ORIGINS`. In Supabase Authentication URL
Configuration, set the production Site URL and allow that origin as an email redirect URL.
The current email-link flow returns to the website root. Avoid broad wildcard redirect rules;
add local development separately if needed. Confirm the chosen plans remain within your budget.

Before inviting Mom or other end users, configure production email delivery. Supabase's default
email service only sends to project-team addresses, so a successful sign-in email to the owner
does not establish that other users can sign in. Follow [Supabase's SMTP setup](https://supabase.com/docs/guides/auth/auth-smtp)
to configure an appropriate provider, review any cost first, and test delivery to the actual end-user
address. Do not give users project-administration membership merely to bypass this restriction.

## Check the deployed services

From `backend/` in the intended Python environment:

```powershell
python scripts/check_deployment.py --api-url https://YOUR-API.onrender.com --frontend-url https://YOUR-SITE.vercel.app --output ../docs/evidence/deployment-check.json
```

The script records seven read-only checks and returns nonzero if any fail. It calls neither the
market-data provider nor embedding APIs and requires no token. It verifies readiness, blocked
unauthenticated watchlists, disabled diagnostic/data routes, the configured frontend CORS origin,
the homepage and manifest. Preserve failed checks, including cold-start failures; do not report
them as passing. Do not commit secrets or authenticated response bodies as evidence.

Then perform the actual user acceptance flow with a real email:

1. Sign in through the delivered link on a laptop. Verify expiry/error behavior is understandable.
2. Analyze one valid ticker and one invalid ticker; check the source-data date and warnings.
3. Add a stock, reload, sign out/in and confirm it remains in the watchlist.
4. Use a different account and confirm it cannot read/remove the first account's saved data.
5. Repeat on a phone; test with the developer laptop off. Installation/offline behavior is a
   separate check, not established by a valid manifest.

This release still has in-process jobs and incomplete prediction evaluation. Restart recovery,
abuse limits, corrected grading and stronger operational monitoring remain open release work.
Do not present the accuracy strip as validated predictive performance. See `delivery-plan.md`.

References checked for this configuration: [Render Blueprint fields](https://render.com/docs/blueprint-spec),
[Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json),
and [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

## Verification checkpoint November 6 2026

The final backend suite passes 118 tests against isolated PostgreSQL and Redis, including browser-role
row-security checks and revocation of prior grants. The actual
production image was built and started with temporary data services and a fixture Supabase URL:
`/ready` and `/health` returned 200, an unauthenticated watchlist request returned 401, and the
disabled database diagnostic returned 404. The existing cache replay also passed with an explicit
test-only authorization override. Raw evidence and source hashes are retained under
`docs/evidence/2026-11-06/deployment/`. This is local container verification, not hosted deployment
or real Supabase authentication. The seven-check deployment script has fixture tests but cannot
run against production until the actual frontend and backend URLs exist.
