# Architecture

Status: Phase A complete. This document records decisions that matter.

## Deployment mode

Single power user, hosted. Not local-first; not multi-tenant SaaS yet.
Every user-owned row carries explicit ownership (`user_id` / `owner_id`) so
multi-user can be layered on without a rewrite, but no unused SaaS machinery
(workspaces-as-tenants, billing, social) is built.

## Key decisions

### 1. Supabase as the Postgres + auth provider (replaces earlier workspace schema)

- Managed Postgres with pgvector on free tier; auth (magic link + Google)
  handled by Supabase Auth. The FastAPI API verifies Supabase JWTs (JWKS,
  ES256/RS256, HS256 fallback) and never sees passwords.
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

Background work (ingestion, embeddings, pathway generation) uses the `jobs`
table with status/progress/attempts/dedupe_key. A small worker loop polls it.
Introduce Redis only when measured need appears.

### 4. Provider abstractions at the boundary (spec §37)

- `LLMProvider` → GeminiProvider (google-genai). Structured generation uses
  response_mime_type=json + response_schema.
- `EmbeddingProvider` → GeminiEmbeddingProvider (text-embedding-004, 768d).
- `WebSearchProvider` → TavilyProvider, ArxivProvider, OpenAlexProvider.
  Ranking/dedup live in the sources domain, not in providers.
- `ObjectStorageProvider` → LocalStorageProvider (dev); S3-compatible later.

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
for lexical search. Semantic (pgvector) + trigram/full-text search wiring lands
with the Search phase.

## What comes next (Phase B onward)

Phase B (Brain) is complete:

- **`GET /api/brain/graph`** — every concept the user has engaged with plus the
  edges between them, with mastery/state/interest per node.
- **Concepts module** — create-with-dedupe (case-insensitive canonical reuse;
  embedding adjudication deferred to Phase C), concept detail with
  prerequisites/unlocks/related, DAG-validated prerequisite edges
  (`app/domain/graph.py`, cycle + self-edge rejected at API with `cycle_detected`).
- **Brain canvas** — Sigma.js WebGL renderer over Graphology: ForceAtlas2
  layout, hover neighborhood emphasis (unrelated nodes/edges fade), selection
  with animated camera focus, domain-colored clusters, mastery-state node
  colors/sizes, zoom controls, domain filter chips.
- **Inspector** — right panel fetching `/api/concepts/{id}`: mastery bar,
  difficulty, description, clickable prerequisite/unlock chips (navigates the
  graph), loading/error states.
- **Accessibility** — list-view alternative (`List` toggle) rendering the same
  data as a semantic, keyboard-navigable outline; ARIA progressbar for mastery.

Integration tests for all brain/concepts endpoints run in CI against a
pgvector service container and skip locally without `DATABASE_URL`.

Next phases:
1. **Source infrastructure** — discovery pipeline, ranking model, chunking +
   embedding jobs, citation model.
2. **Pathways** — structured generation with DAG validation via
   `app/domain/graph.py`.
3. **Grounded learning** — lesson pipeline with claim→source attribution.
