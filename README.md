# Lattice

A personal, hosted learning platform: a persistent map of what you know, source-grounded
lessons, pathways, spaced review, and an AI guide — inspired by the publicly observable
BirdsEyes product experience, implemented entirely from scratch on open infrastructure.

**Status:** hosted pilot. The web app runs on Vercel, the API/worker runs on Render,
and Supabase provides the database, vector search, and authentication.

**Live deployment:** [web app](https://web-five-omega-34.vercel.app/) ·
[API health](https://lattice-1gym.onrender.com/api/health)

## What is working

- Brain graph with domain-colored concepts and mastery state
- Automatic source classification, ranking, chunking, and embeddings
- AI-generated pathways, grounded lessons, quizzes, reviews, and discovery
- URL and note sources; private Supabase Storage supports opt-in portrait photos
- Supabase magic-link/Google auth with a production email allowlist

## Stack

| Layer     | Choice                                                        |
| --------- | ------------------------------------------------------------- |
| Frontend  | Next.js 15 · React 19 · TypeScript strict · Tailwind v4 tokens · TanStack Query · Zustand · Motion |
| Backend   | FastAPI · SQLAlchemy 2 async · Alembic · Pydantic v2          |
| Database  | Supabase PostgreSQL + pgvector (HNSW)                         |
| Auth      | Supabase Auth (magic link + Google OAuth), JWT verified in API |
| AI        | Gemini via `LLMProvider` abstraction                          |
| Discovery | Tavily (web) + arXiv + OpenAlex (academic) behind `WebSearchProvider` |

## Repository layout

```
lattice/
├── apps/
│   ├── web/    # Next.js frontend
│   └── api/    # FastAPI backend
├── docs/       # architecture, deployment, handoff, provenance, decisions
├── scripts/    # dev helpers
└── .env.example
```

## Development setup

### Backend (Windows PowerShell)

```powershell
cd apps\api
py -3 -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"   # or: pip install -e .
copy ..\..\.env.example ..\..\.env        # then fill in real values

# apply schema to your Supabase project
alembic upgrade head

# run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd apps\web
npm install
copy .env.example .env.local              # fill in Supabase URL + anon key
npm run dev                               # http://localhost:3000
```

### Supabase console checklist

1. Enable **Google OAuth** provider (Authentication → Providers).
2. Add redirect URL `http://localhost:3000/auth/callback`.
3. Note the **anon key** (web) and **service role key** (API only).

## Production deployment

The production split is:

- **Supabase:** Postgres, pgvector, and Auth
- **Render:** FastAPI API and Postgres-backed worker
- **Vercel:** Next.js web app

Follow [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete setup. The
Render API must include:

```text
ENVIRONMENT=production
WEB_ORIGIN=https://your-vercel-domain.vercel.app
ALLOWED_EMAILS=you@example.com,another@example.com
```

`ALLOWED_EMAILS` is enforced by the API for every protected route. Keep the
Supabase service-role key, database password, and provider keys on Render only.
For a Free Render service, append `&& alembic upgrade head` to the build command
(`pip install . && alembic upgrade head`) so the schema is upgraded before the
Uvicorn start command. Create the `lattice-private` Supabase Storage bucket as
private before enabling portrait photos or PDF uploads. Paid services can use
Render's pre-deploy command instead.

## Testing

```powershell
cd apps\api
pytest            # unit tests (no DB required for graph/config tests)
ruff check app
```

```powershell
cd apps\web
npm run typecheck
npm run build
```
