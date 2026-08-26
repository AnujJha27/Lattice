# Lattice

A personal, hosted learning platform: a persistent map of what you know, source-grounded
lessons, pathways, spaced review, and an AI guide — inspired by the publicly observable
BirdsEyes product experience, implemented entirely from scratch on open infrastructure.

**Current status:** Phase A (hosted foundation) — see `docs/architecture.md`.

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
├── docs/       # architecture, data model, provenance, decisions
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
