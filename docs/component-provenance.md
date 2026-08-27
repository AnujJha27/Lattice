# Component Provenance

Every significant reused or adapted component is recorded here. Custom
product-specific code (Brain interactions, pathway behavior, grounded-lesson
UI, and review/discovery flows) is built on these primitives.

## Phase A — Foundation

| Component | Upstream | License | Version | Usage | Modifications |
| --- | --- | --- | --- | --- | --- |
| Next.js app router, layout, route handlers | vercel/next.js | MIT | 15.x | App shell, auth callback route, middleware | Lattice pages/tokens |
| Tailwind CSS | tailwindlabs/tailwindcss | MIT | 4.x | Styling engine; CSS-first config | Custom design tokens in `app/globals.css` (§49) — no default shadcn aesthetics |
| TanStack Query | TanStack/query | MIT | 5.x | Server state (`useQuery` in app shell) | Default options tuned in `providers.tsx` |
| Supabase JS + SSR helpers | supabase/supabase-js · supabase/ssr | MIT | 2.x / 0.6.x | Auth session management, cookie refresh | Standard `@supabase/ssr` cookie pattern; API-side JWT verification and production email allowlist are Lattice code |
| lucide-react | lucide-icons/lucide | ISC | latest | Icons | None |
| clsx + tailwind-merge | (lukeed/clsx) (dcastil/tailwind-merge) | MIT | 2.x | `cn()` class utility | None |
| FastAPI | fastapi/fastapi | MIT | 0.115+ | HTTP framework | App factory, custom error schema |
| SQLAlchemy 2 async + asyncpg | sqlalchemy/sqlalchemy · MagicStack/asyncpg | MIT / Apache-2.0 | 2.x | ORM + async driver | Declarative models with naming convention |
| Alembic | sqlalchemy/alembic | MIT | 1.14+ | Migrations | Async env.py per upstream recipe |
| Pydantic v2 + pydantic-settings | pydantic/pydantic | MIT | 2.x | Config + validation | `Settings` bound to env vars |
| pgvector-python | pgvector/pgvector-python | PostgreSQL/MIT | 0.3+ | `Vector` column type + HNSW indexes | None |
| google-genai | googleapis/python-genai | Apache-2.0 | 0.5+ | GeminiProvider + `gemini-embedding-001` embeddings behind our abstractions | Wrapped by `LLMProvider`/`EmbeddingProvider` protocols |

## Phase B — Brain

| Component | Upstream | License | Version | Usage | Modifications |
| --- | --- | --- | --- | --- | --- |
| Sigma.js (WebGL renderer) | jacomyal/sigma.js | MIT | 3.x | Brain canvas: pan/zoom camera, hit testing, label LOD, node/edge reducers for hover emphasis | Custom reducers (neighborhood emphasis, selection), mastery/domain color mapping, zoom controls |
| Graphology | graphology/graphology | ISC | 0.25.x | In-memory graph structure feeding Sigma | None |
| graphology-layout-forceatlas2 | jacomyal/sigma.js (packages) | MIT | latest | Initial layout (120 sync iterations; worker variant planned at >1k nodes) | `inferSettings` defaults |
| zustand | pmndrs/zustand | MIT | 5.x | Brain UI interaction state (hover/select/filter/view-mode) — deliberately *not* used for API state | None |
| Motion | motiondivision/motion | MIT | 11.x | Page transitions, loading states, and UI motion | Product-specific timing and reduced visual noise |
| Three.js + React Three Fiber | mrdoob/three.js · pmndrs/react-three-fiber | MIT | 0.18x / 9.x | Nebula/starfield background visuals | Lattice scene composition and effects |

## Phase C — Source infrastructure

| Component | Upstream | License | Version | Usage | Modifications |
| --- | --- | --- | --- | --- | --- |
| Tavily API client | tavily-ai/tavily (HTTP) | proprietary SaaS (MIT SDK examples) | v1 API | General web search behind `WebSearchProvider` | Custom httpx client; normalized to SearchHit |
| arXiv API | arxiv.org help/api | open data | Atom API | Academic preprint search; arXiv IDs persisted for dedup | Custom Atom XML parser |
| OpenAlex API | ourresearch/openalex | CC0 data | v1 API | Scholarly metadata, DOIs, citation counts | Custom client; author/DOI extraction |

Ranking, classification, dedup, chunking, extraction, lesson rendering,
pathway validation, review scheduling, and recommendation logic are
Lattice-original implementations encoding the product requirements.

## Planned, not currently integrated

| Component | Candidate upstream | Intended use |
| --- | --- | --- |
| Pathway DAG editor | xyflow/xyflow (React Flow) | Explicit prerequisite DAG interactions |
| Command palette | pacocoursey/cmdk | Global search palette (spec §20) |
| Toasts | emilkowalski/sonner | Notifications |
| Primitives | Radix UI primitives (radix-ui/primitives) + shadcn/ui patterns | Dialogs/menus/popovers with heavy custom styling (spec §2) |
| Rich text | ueberdosis/tiptap | Notes editor (spec §23) |
| Math rendering | KaTeX or MathJax equivalent | LaTeX in lessons (overrides §30) |
| Durable object storage | S3-compatible provider | Production PDF uploads, signed URLs, and resumable uploads |
