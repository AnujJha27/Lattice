# Lattice deployment

Recommended first deployment: Supabase for Postgres/Auth, Render for the FastAPI worker/API, and Vercel for Next.js. Keep the API and web app as separate services; the API process starts the Postgres-backed job worker with FastAPI lifespan.

## 1. Prepare Supabase

1. Create or choose a Supabase project and enable the `vector` extension.
2. In `apps/api`, run the migrations against the production database:

   ```powershell
   .\.venv\Scripts\alembic.exe upgrade head
   ```

3. Configure Auth providers and add the production callback URL:
   `https://YOUR_WEB_DOMAIN/auth/callback`.
4. Keep the database password, service-role key, and API keys private. Only the anon key belongs in the browser.

## 2. Deploy the API on Render

Create a **Web Service** from this repository:

- Root directory: `apps/api`
- Runtime: Python 3.12+
- Build command: `pip install . && alembic upgrade head`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`

Set these environment variables in Render:

```text
ENVIRONMENT=production
WEB_ORIGIN=https://YOUR_WEB_DOMAIN
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=lattice-private  # private bucket for opt-in portrait photos
ALLOWED_EMAILS=aj05767625@gmail.com,aj472032@gmail.com,aniruddh302004@gmail.com
GOOGLE_API_KEY=...
GOOGLE_API_KEYS=...               # optional comma-separated backup Gemini keys
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=...
TAVILY_API_KEY=...
SUPABASE_JWT_SECRET=...        # only for projects using the legacy JWT secret
```

After deploy, verify `https://YOUR_API_DOMAIN/api/health` and `https://YOUR_API_DOMAIN/docs` (docs are disabled automatically when `ENVIRONMENT=production`).

`ALLOWED_EMAILS` is a comma-separated production allowlist. The API rejects signed-in users whose email is not listed.

### Object storage requirement

Production `make_storage()` uses Supabase Storage for private portrait photos
and PDF uploads when `SUPABASE_SERVICE_ROLE_KEY` and
`SUPABASE_STORAGE_BUCKET` are set. Create a private bucket named
`lattice-private` (or the configured name) in Supabase Storage. The API streams
photos only after authenticating the owning user; do not expose the service-role
key to Vercel. Do not switch production to local storage: Render disks are
ephemeral.

## 3. Deploy the web app on Vercel

Import the repository as a Vercel project:

- Root directory: `apps/web`
- Framework preset: Next.js
- Install command: `npm ci`
- Build command: `npm run build`

Set:

```text
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=https://YOUR_API_DOMAIN
```

Add the Vercel domain to Supabase Auth redirect URLs and set the API `WEB_ORIGIN` to the exact Vercel origin (no trailing slash).

## 4. Verify the deployed loop

1. Sign in with the magic link or Google OAuth.
2. Add an interest and confirm it appears in `/api/brain/graph`.
3. Create a beginner pathway; wait for its status to become `READY`.
4. Open a concept, generate/read its lesson, answer a quiz, and confirm mastery changes.
5. Open Review and Discovery; confirm due reviews, recommendation events, and portrait snapshots appear.
6. Save a URL or note. Test PDFs only after object storage is configured.

The migration must remain in the build command for a Free Render service,
because Free Web Services do not provide a pre-deploy command. It applies
schema changes before the new API process starts; do not put `alembic upgrade
head` in the long-running start command. If the service is upgraded to a paid
instance, move the migration to Render's pre-deploy command instead.

## 5. CI and releases

Pushes to `main` run `.github/workflows/ci.yml`. Merge only when web typecheck/build, API lint/tests, and migration SQL generation pass. On the Free Render service, the build command applies `alembic upgrade head` before the API starts.

## Rollback

Vercel can promote the previous deployment instantly. For the API, redeploy the previous commit. Do not downgrade migrations automatically; create a forward migration for production data changes.
