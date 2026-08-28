# Architecture

Status: hosted pilot. This document records decisions that matter.

## Deployment mode

Single power user, hosted on Supabase, Render, and Vercel. Not local-first;
not multi-tenant SaaS yet.
Every user-owned row carries explicit ownership (`user_id` / `owner_id`) so
multi-user can be layered on without a rewrite, but no unused SaaS machinery
(workspaces-as-tenants, billing, social) is built.

The browser runs on Vercel, while Render runs the FastAPI API and
Postgres-backed worker. Supabase owns Postgres, pgvector, and Auth. Production
API access is restricted by `ALLOWED_EMAILS`, and `WEB_ORIGIN` is the exact
Vercel origin used for CORS.

## Key decisions

### 1. Supabase as the Postgres + auth provider (replaces earlier workspace schema)

- Managed Postgres with pgvector on free tier; auth (magic link + Google)
  handled by Supabase Auth. The FastAPI API verifies Supabase JWTs (JWKS,
  ES256/RS256, HS256 fallback) and never sees passwords.
- The API rejects valid Supabase sessions whose email is not in
  `ALLOWED_EMAILS`; the service-role key remains server-only.
- The earlier draft schema modeled workspaces + members for RLS-driven
  tenancy. Dropped: single user makes that indirection pure cost. Ownership is
  now direct `profiles.id` references. RLS remains enabled on sensitive tables
  as defense-in-depth behind the API's explicit scoping.
- Alembic owns the public schema; Supabase owns `auth.*`. The only cross-schema
  reference is `profiles.id → auth.users.id`, declared in the baseline migration.

### 2. Canonical concepts vs per-user state (spec §33)

`concepts` holds shared canonical records (scope GLOBAL) plus private USER
concepts owned by a profile. Learning state lives exclusively in
`user_concepts` (mastery, review scheduling fields, interest). Never duplicate
concept content into user state.

### 3. PostgreSQL job table instead of Redis/Celery (spec overrides §6)

Background work (ingestion, embeddings, pathway generation, and portrait
recomputation) uses the `jobs` table with status/progress/attempts/dedupe_key.
A small worker loop polls it.
Introduce Redis only when measured need appears.

### 4. Provider abstractions at the boundary (spec §37)

- `LLMProvider` → GeminiProvider (google-genai). Structured generation uses
  response_mime_type=json + response_schema.
- `EmbeddingProvider` → GeminiEmbeddingProvider (`gemini-embedding-001`, 768d).
- `WebSearchProvider` → TavilyProvider, ArxivProvider, OpenAlexProvider.
  Ranking/dedup live in the sources domain, not in providers.
- `ObjectStorageProvider` → LocalStorageProvider (dev) and
  SupabaseStorageProvider (production). Private portrait photos and PDF
  uploads use the configured Supabase bucket; Render disks remain out of the
  storage path.

No feature module imports an SDK directly.

### 5. Graph algorithms in plain Python over edge tuples

`app/domain/graph.py` implements cycle detection, topological ordering, and
ancestor queries on `(src, dst)` tuples — ORM-free and unit-tested. Recursive
CTEs will handle large traversals later; NetworkX is unnecessary at this scale.

### 6. Stable error schema & request IDs

Every failure returns `{ error: { code, message }, request_id }`. The web
client normalizes these into `ApiError`. Middleware propagates
`x-request-id` through logs via contextvar.

## Data model (baseline)

```
profiles ─┬─< goals ──< goal_concepts >── concepts ──< concept_edges
          ├─< pathways ──< pathway_sections ──< pathway_concepts
          └─< user_concepts >──────────────────────┘   (mastery/review state)

sources ──< source_chunks (+ embedding vector(768))
concepts ──< concept_sources >── sources

lessons ──< lesson_sources >── sources      (provenance)
prompt_versions / ai_generations            (cost + traceability)
jobs                                        (Postgres-backed queue)
```

pgvector HNSW indexes exist on `concepts.summary_embedding` and
`source_chunks.embedding`; `concepts.name_tsv` is a generated tsvector column
for lexical search.

## Current capabilities

- **Brain and concepts** — graph retrieval, case-insensitive and
  embedding-assisted dedupe, domain-aware clusters, mastery state, graph
  inspection, and DAG-validated prerequisite/related edges.
- **Sources** — URL, note, and private PDF ingestion, trust-based
  classification, Tavily/arXiv/OpenAlex discovery, ranking, dedupe, extraction,
  chunking, and Gemini embeddings.
- **Pathways and lessons** — asynchronous structured generation, validated
  pathway DAGs, on-demand grounded lessons, inline citations, and quizzes.
- **Review and discovery** — mastery updates, spaced review scheduling,
  recommendations, portrait snapshots, and feedback events.
- **Web experience** — Next.js app shell, Supabase SSR sessions, Sigma.js
  WebGL graph, semantic SVG portrait renderer, optional private profile photo,
  eight portrait themes, SVG/PNG share-card editions, accessible list/text
  views, responsive lesson reader, and shared loading/error states. The
  renderer split and tradeoffs are recorded in `docs/portrait-rendering.md`.

Integration tests run in CI against a pgvector service container and skip
locally without `DATABASE_URL`; graph, validation, citation, and source-domain
logic also have focused unit tests.

## Next priorities

1. Improve review calibration and recommendation evaluation.
2. Add source search, folders, tags, and re-ingestion/version metadata.
3. Add deletion/export controls and encryption-at-rest policy for user content.

Social sharing, teams, billing, and a plugin ecosystem remain out of scope
until the single-user learning loop is measurably useful.
