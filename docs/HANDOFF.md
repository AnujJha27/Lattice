# Lattice — Handoff Document
**Last updated:** 2026-08-28 — roadmap, source-ingestion, and learning-loop recheck  
**Branch:** `main` · **Repo:** `D:\fun stuff\lattice`  
**Dev URLs:** `http://localhost:8000` (API) → `http://localhost:3000` (web)  
**DB:** Supabase `bkqlshzbxjulkredbdyq` (ap-northeast-1) · pgvector `vector` extension enabled  
**LLM primary:** OpenRouter `z-ai/glm-5.2:free` → fallback pool `nemotron-3-ultra-550b:free` → `nemotron-3-super-120b:free` → `minimax-m3:free` (sticky 429 rotation, 90s backoff)  
**Embeddings:** `gemini-embedding-001` (768-dim, `output_dimensionality: 768`) — `text-embedding-004` is retired (404)  
**Browser note:** hard-refresh `Ctrl+Shift+R` after deploys (stale chunk cache caused the `intuition` crash). `suppressHydrationWarning` is on `<html>`.

---

## 1. Mission (verbatim from spec)
> Build **Lattice**, a production-grade hosted learning platform that recreates the complete publicly observable product experience of **BirdsEyes** — Brain, interests, pathways, lessons, exercises, review, discovery, source ingestion, personalization, AI guidance, knowledge persistence — using our own implementation/infra/branding.

**Target is NOT** a prototype/MVP/dashboard/graph demo/shadcn template. Target is a polished, source-grounded, persistent personal observatory for one power user, deployable via CI, secure, backed by PostgreSQL+pgvector, structured-generation validated (Pydantic), cost/logged, and extensible toward full BirdsEyes parity.

**Overrides:** single-user, free-tier-first (but replaceable providers), Redis/queues via Postgres job table, source-first (not parametric LLM memory), billing+social deferred.

---

## 2. What Has Been Built (Phases A–E)

### Phase A — Hosted Foundation ✅
- **Monorepo:** `apps/api` (FastAPI) + `apps/web` (Next.js 15 App Router, React 19, TS strict, Tailwind v4)
- **Config:** `app/core/config.py` now resolves `.env` at repo root via `Path(__file__).parents[4]` + CWD fallback (fixes `parents[3]` off-by-one that pointed at `apps/` and fell back to `postgres:postgres@localhost` → misleading `InvalidPasswordError` for user `postgres`)
- **DB:** SQLAlchemy 2 async + Alembic
  - `alembic/versions/0001_baseline.py` — full schema (extensions `vector`, `pgcrypto`; enums; tables: `profiles`, `concepts` (generated `tsvector` via `Computed`), `concept_edges`, `user_concepts`, `goals`/`goal_concepts`, `pathways`/`pathway_sections`/`pathway_concepts`, `sources`/`source_chunks` (`vector(768)` HNSW), `concept_sources`, `lessons`/`lesson_sources`, `prompt_versions`/`ai_generations`, `jobs`)
  - `0002_job_timestamps.py` — adds `jobs.created_at/updated_at` (FIFO polling)
- **Provider abstractions:** `LLMProvider` (Gemini), `EmbeddingProvider` (Gemini 768), `WebSearchProvider` (Tavily + arXiv + OpenAlex), `ObjectStorageProvider` (Local dev + Supabase private storage)
- **Factory:** `providers/factory.py` — `get_llm_provider()` → OpenRouter when `OPENROUTER_API_KEY+OPENROUTER_MODEL` set, else Gemini
- **Auth:** Supabase Auth (magic-link + Google OAuth). API verifies JWT via `PyJWKClient` → JWKS `ES256/RS256` + HS256 fallback (`SUPABASE_JWT_SECRET`). `profiles.id → auth.users.id` (FK declared only in migration). `ensure_profile(session, user_id, email)` auto-mirrors auth user; called by concept/pathway/source/lesson routes and by `ensure_user_concept` to prevent `FK user_concepts_user_id_profiles` violations.
- **Errors/Observability:** unified `{error:{code,message}, request_id}`; `RequestContextMiddleware` (`x-request-id` + JSON logs + access log); `/api/health` reports llm/embeddings/web_search/academic
- **CI:** `.github/workflows/ci.yml` — web typecheck+build, api `ruff+pytest` against a migrated `pgvector/pgvector:pg16` service, and alembic offline SQL check; the API job supplies a minimal Supabase auth stub for migrations.
- **Env:** `.env.example` (root) + `apps/web/.env.local` (NEXT_PUBLIC_*). Root `.env` is the source of truth for the API.

### Phase B — Brain ✅
- **Service:** `app/modules/brain/service.py` — `get_brain_graph`, `get_or_create_concept` (now semantic dedup), `ensure_user_concept`, `add_edge` (DAG-validated via `domain/graph.py`, also links both endpoints into the user's Brain, `RELATED_TO`/`PREREQUISITE`/`PART_OF`)
- **Graph utils:** `app/domain/graph.py` — `ensure_acyclic`, `topological_order`, `ancestors` (edge-tuple, ORM-free, unit-tested)
- **API:** `GET /api/brain/graph`, `POST /api/concepts`, `GET /api/concepts/{id}` (prereqs/dependents/related), `POST /api/concepts/{id}/edges`, `POST /api/concepts/combine` (BirdsEyes Fuse)
- **Frontend:** Sigma.js + EdgeCurve, ForceAtlas2, Louvain communities, NebulaSky shader sky
  - `components/brain/BrainCanvas.tsx` — curved edges (`EdgeCurveProgram`), cinematic entrance, hover ink-plate labels (`defaultDrawNodeHover`: ink bg + brass border + parchment text), degree-weighted hub sizes, community→domain ring layout, size-aware cluster radii, centroid repulsion (minSep per-cluster), drag-to-move, focus pan (no aggressive zoom), highlight dull on pick/hover, `store.subscribe(refresh)`
  - Focused-island labels now remain visible for low-mastery concepts and after drill-down with a prior selection; stale overview hover IDs are ignored so the reducer cannot blank the focused island.
  - `components/ui/NebulaSky.tsx` — R3F WebGL `Canvas` with `dpr=[1,1.5]`, fbm nebula fragment shader (ink/indigo/brass), parallax on mouse, star layer (500-700 points, calmer twinkle `0.8–1.0`, large blur removed), `powerPreference: high-performance`, `antialias: false`; now only on page-level (sidebar is CSS nebula to avoid multi-context throttling/flicker)
  - `components/ui/Shimmer.tsx` — `Shimmer` + `ShimmerRows` (brass sweep, no `animate-pulse` left anywhere)
  - Store `lib/store/brain.ts` — `hoveredId/selectedId/viewMode/domainFilter/combineMode/combinePicks` + `neighborsOf/visibleNodes`
  - `components/brain/Inspector.tsx` + `BrainListView.tsx` + `AddInterest` + detail hooks

### Phase C — Source Infrastructure ✅
- **Classify/ranking/dedup:** `sources/classify.py` (trust hierarchy by host/TLD, `OFFICIAL_DOCS > STANDARDS > ACADEMIC > GOV > UNIV > REFERENCE > BLOG/FORUM`), `sources/ranking.py` (domain-aware `S = w_a·A + w_r·R + w_f·F + w_p·P`, `freshness = 2^(-age/2)`), `sources/dedup.py` (DOI > arXiv > canonical URL, tracking-param stripping), `discovery.py` (fan-out, dedup, rank), `extraction.py`, `chunking.py`
- **API:** `POST /api/sources/discover` (ranked candidates + factor breakdown), `POST /api/sources` (dedup + link to concept + enqueue `SOURCE_INGEST`), `GET /api/sources`, `POST /api/retrieval/query` (pgvector cosine over `source_chunks`)
- **Providers:** `providers/arxiv.py` (`https` + `follow_redirects`), `providers/openalex.py` (sanitize punctuation, no `mailto`), `providers/tavily.py`
- **Jobs:** `app/jobs/queue.py` (`enqueue_job` with dedupe, `claim_next_job` with `SKIP LOCKED`), `app/jobs/handlers.py` (`handle_source_ingest`: fetch→extract→chunk→Gemini embed→HNSW, `handle_pathway_generation`, `handle_lesson_generation`), `app/jobs/runner.py` (`worker_loop`, `recover_stuck_jobs`, sticky rotation, 90s on 429)

### Phase D — Pathways ✅
- **Schema/Generation:** `modules/pathways/schemas.py` (`GeneratedConcept/Section/Pathway`), `generator.py` — `SYSTEM_PROMPT` demands structured sections+concepts+prereqs, DAG-enforced, deduped against canonical store, cross-domain `RELATED_TO` bridges (embed pathway concepts, persist `summary_embedding`, backfill 30 old concepts, nearest different-domain neighbour if distance <0.55, max 4 bridges)
- **API:** `POST /api/pathways` (202, `GENERATING` + job), `GET /api/pathways` (list), `GET /api/pathways/{id}` (sections+concepts with mastery), `DELETE /api/pathways/{id}` (orphan-concept sweep: delete concepts with zero other pathways/edges/lessons)
- **Frontend:** `app/app/pathways/page.tsx` + `[id]/page.tsx` (composer with depth, live polling, per-card generating shimmer, delete with confirm, detail with numbered layers)

### Phase E — Grounded Learning (part 1) ✅
- **Schema:** `modules/lessons/schemas.py` — `LessonParagraph/Section/Content` (v2 book-chapter: `intuition` + 4–8 `sections` each 2–4 paras + equations + key_points, legacy `paragraphs` kept), `SourceContext`, `LessonOut`
- **Context:** `modules/lessons/context.py` — `gather_contexts` (pgvector retrieval over `EMBEDDED` chunks, fallback discovery snippets)
- **Generator:** `modules/lessons/generator.py` — `validate_citations` (strips fabricated `source_ids`), `grounding_status` (`GROUNDED/MIXED/GENERATED`), `_coerce_payload` (fuzzy key fix for free-model typos like `keheading → heading`), single `AIGeneration` row per attempt, provenance via `lesson_sources`
- **Routes:** `POST /api/concepts/{id}/lesson` → 202 (enqueue `LESSON_GENERATION`), `GET .../lesson` (cached, 404 until ready)
- **Frontend:** `app/app/concepts/[id]/page.tsx` — book rendering (numbered serif headings, `CitedParagraph`/`CitationMarker`, per-section equations plates, "Retain" callouts, source chips; legacy flat fallback; async generation with queued flag + polling, orbit+ sweep loading, hard-refresh-safe guards)

### Design System — Observatory ✅
- **Tokens:** `app/globals.css` — ink `#0A0E1A`, chart line `#232C42`, parchment `#EAE5D9`, brass `#C9A961`, mastery scale (slate→ice→warm white→gold), radii 4/7/12, shadows, motion easings, `font-display` (Spectral 300-600), `font-body` (Hanken Grotesk), `font-mono` (IBM Plex Mono)
- **Layout:** `app/layout.tsx` — `next/font` wired, `suppressHydrationWarning` on `<html>` (fixes `dark` vs `dark hydrated` mismatch)
- **Effects:** `Starfield.tsx`, `Spotlight.tsx` (`SpotlightCard`, `ShimmerText`, `BorderBeam`), `NebulaSky.tsx`, `Shimmer.tsx`, `effects.tsx` (`Reveal`, `CountUp`, `AuroraBackground`, `BorderBeam`, `Magnetic`)
- **Shell:** `components/shell/Sidebar.tsx` — static CSS nebula (no WebGL), glass panel, gradient wordmark, `Sparkles` eyebrow, brass active bar

---

## 3. Current Dev Health
- **Backend:** running at `http://127.0.0.1:8000`; `GET /api/health` shows `openrouter:z-ai/glm-5.2:free`, `web_search:tavily`, `academic:[arxiv,openalex]`; pathway generation cycling after 429s is healthy (sticky rotation now recovers)
- **Frontend:** `apps/web` — direct TypeScript check ✅; production build is not runnable in this WSL1 checkout because the npm wrapper rejects WSL1 and the direct Next binary lacks its optional Linux SWC package. Run the build from WSL2/Windows after dependencies are installed; no application compile error has been observed here.
- **Tests:** `apps/api` non-DB suite (excluding the local TestClient hang) — 114 passed; portrait/visual/golden tests — 33 passed; portrait/learning integration — 11 skipped without disposable `DATABASE_URL`; focused web checks — 5 JavaScript files pass plus compiled Brain checks — 3 passed; direct TypeScript typecheck and Python compilation pass; full-repo Ruff is clean

---

## 4. Known Issues — What You Flagged (and What's Left)

> Every flickery `animate-pulse` has been replaced with `Shimmer` (brass sweep). Sidebar bg bug (invalid multi-layer `background` shorthand) is fixed to `backgroundColor + backgroundImage`. If something still flickers after a hard refresh, note the route + action — it is likely a WebGL-context or `refetchInterval` polling cause.

| # | Report | Root cause | Fix in code | Still needs |
|---|--------|------------|-------------|-------------|
| 1 | **Background flicker / dead space** | CSS blur auroras (60vw `blur(110px)`) repaint hell + multi-WebGL contexts | `NebulaSky` single shader (fbm + stars + parallax) replaces CSS aurora; star twinkle calmed (`0.55→0.8`), `dpr [1,1.5]`; sidebar is CSS-only; overview tightened (`max-w-3→5xl`, brass shimmer headline, CountUp) | Visual tuning — check Overview + Login full-bleed; report if nebula density/glow needs dialling |
| 2 | **Brain: all points same spot** | FA2 repulsion with `x:0,y:0` for all nodes → zero forces | Golden-angle spiral seeding + `louvain.assign` community ring + size-aware radii + centroid repulsion (enforced `minSep`) + degenerate-layout guard |
| 3 | **Brain: no connecting lines** | Default edge color `rgba(...,0.06)` near-invisible | Default `rgba(201,169,97,0.30)` `size 1.6`; selected/hovered → `rgba(232,205,140,0.95)` `size 2.6`; uses `EdgeCurveProgram` |
| 4 | **Brain: FV in middle of ML cluster** | `domain` string of FV was ML-adjacent; layout used domain labels, not edges | Now clusters by **Louvain-detected communities**; when only one community, falls back to domain. *Requires an actual edge* FV↔Category Theory — see cross-domain bridges below |
| 5 | **Psych too close to ML** | Fixed ring radius + weak repulsion = overlap | Size-aware ring (`radius ∝ sqrt(share)`) + per-pair `minSep = 10 + 0.4·(sizeA+sizeB)` over 2 passes + gravity `0.32` |
| 6 | **Map superimposes different topic graphs** | Louvain merged everything ( `communityCount==1` → single centroid) and the guard that restores domains was removed | Restored: if `communityCount <= 1`, strip `__community__` so domain ring takes over |
| 6b | **Brain still one hairball after EIS purge (2026-08-26 night)** | Domain column is `NULL` for **56/57** concepts, so domain-ring produced one giant `Uncategorized` island (56 nodes). Louvain had been disabled, making it worse. Screenshot at 23:35 showed all wires solid again. | **Fixed 23:45:** reverted to Louvain `resolution 0.65` (community islands), removed `hidden` on cross-cluster edges → ghosted `0.14` alpha (visible but whispered), removed global ForceAtlas smear, size-aware ring + per-pair `minSep`. Code at `BrainCanvas.tsx:84` is now Louvain; needs hard-refresh after `rm -rf .next` + `npm run dev`. |

| 7 | **Map disappears on node click** | `focusNode` did `ratio / 2` each click → repeated clicks zoom infinitely; reducers not refreshed on `selectedId` change | `focusNode` now clamps `ratio ∈ [0.7,1.4]`; added `store.subscribe(() => sigma.refresh())` |
| 8 | **Fuse 405 `Method Not Allowed`** | `/concepts/combine` declared inside a `prefix="/concepts"` router → real path was `/concepts/concepts/combine` | Changed to `@router.post("/combine")` → `/api/concepts/combine` (verified: 401 not 405) |
| 9 | **Fuse / pathway generation 429s** | Free tier per-minute rate limits; backup job path hit `MissingGreenlet` after rollback; embedding model `text-embedding-004` 404 | Sticky model-pool cycling (`DEFAULT_FALLBACKS`), 90s backoff on 429, snapshotted `attempts/max_attempts` before rollback; `gemini-embedding-001` with 768-dim |
| 10 | **Lesson doesn't generate / 404 `text-embedding-004`** | Retired model | `gemini-embedding-001` + `output_dimensionality:768`; `openrouter` 429s now cycle; `RankedCandidate.factors` typed `float` but contained `policy:str` → `dict[str,Any]`; arXiv `http→https+follow_redirects`; OpenAlex `mailto` removed + punctuation sanitize |
| 11 | **Lesson loading still flickery + pathway loading after generation** | `animate-pulse` everywhere + WebGL flicker + step-text gap (`AnimatePresence mode="wait"`) | All `animate-pulse` → `Shimmer`; step text `mode="wait"` → overlapping crossfade; `ConceptPage` guard `lesson.data?.content?.intuition`, async lesson generation (POST 202 + poll GET every 3s) so no long-sync timeout |
| 12 | **Lesson should be bigger (book-chapter depth)** | Old prompt: `intuition + 3-4 paras` | New prompt: 6–8 sections × 3–5 paras, worked examples, pathologies, connections — costs ~20–33k output tokens, 3–6 min; async job avoids UI timeout |
| 13 | **`intuition` crash after generation** | Browser cache held stale 202 response as lesson data + free model typo `keheading` → validation failure | Frontend guard `lesson.data?.content?.intuition`; backend `_coerce_payload` fuzzy key snapping (`difflib 0.8`) |
| 14 | **Usage pipeline double counts** | Two `AIGeneration` inserts per lesson | Single snapshot row per attempt (success or failure) via `generation_row`; 429 no-choices cycling; `choices` missing → cycle; duplicate rows deleted (4 removed) |
| 15 | **Delivery flow / milestones / Observability** | No single view | This handoff + `ai_generations`/`jobs` health queries (see §7) |

**Still requiring runtime verification:**
- **Local test-client note:** this checkout's Python 3.14 + AnyIO `BlockingPortal` hangs even with a minimal FastAPI `TestClient`; the pure API suite passes when `test_api.py` and the disposable-DB module are excluded. CI's Python 3.12 job remains authoritative for the TestClient/integration path.
- **Brain visual check:** after a clean dev restart, confirm Louvain islands remain separated and focused-island labels stay visible after selecting a concept in the overview.
- **Production redeploy check:** confirm failed source/embedding jobs become `FAILED` or backoff `PENDING`, never stranded `RUNNING`; confirm the root status response and `/api/health`.
- **Disposable database CI:** run the migration plus integration job against Postgres/pgvector.
- **Browser coverage:** run responsive screenshots and the portrait interaction flow in a browser-capable environment.

---

## 5. Immediate TODOs (what to do first, in order)

| Priority | Task | Where | Done when |
|----------|------|-------|-----------|
| **P0** | **Redeploy the current API fixes** — worker rollback safety, remote PDF extraction, and root status route | Render API | `/` and `/api/health` return 200; failed jobs settle cleanly |
| **P0** | **Run the disposable Postgres/pgvector CI job** — apply head migrations, then run integration tests | `.github/workflows/ci.yml` | Migration and integration job pass in CI |
| **P1** | **Run browser portrait verification** — sparse, mature, inspector, island drill-down, and mobile layout | Profile/Brain | Main interaction and responsive checks pass |
| **P2** | **Verify the institutional visual fallback in deployment** | `modules/visual_sources/providers/*` | The Met fallback is reachable and preserves rights/provenance fields in a real refresh |
| **P2** | **Run the Phase 6 presentation gate** — themes/export/generated editions | `docs/FUTURE_STEPS.md` §§58–60 | Browser-check the eight themes and SVG/PNG downloads; artwork remains optional and non-authoritative |

---

## 6. Phase F — Plan (what's next, detailed)

Per **main spec §15–19 + overrides Phase F** — the closing loop `quiz → mastery update → review scheduling → next recommendation → Brain evolution`.

### F1. Data model (Alembic migration `0003`)
- `quiz_questions` (if not as jsonb), `quiz_attempts`/`quiz_answers` already exist as `quizzes` + `quiz_attempts`; add if missing
- `reviews` — `reviews` table or reuse `user_concepts.next_review_at` + `reviews` log (attempt, correctness, latency, confidence)
- Ensure `user_concepts.mastery_score/state/next_review_at` are indexed (`user_concepts_review` exists)

### F2. Mastery
- Keep deterministic scoring (`0..100`, `UNSEEN/AVAILABLE/LEARNING/FAMILIAR/MASTERED/REVIEW_DUE`); on quiz submit: recompute mastery via exponential moving average or simple increment/decrement; update `last_tested`
- Make Brain colors react instantly via `nodeColorResolver(mastery)` (already wired; will verify)

### F3. Spaced review (scheduler)
- Server-side `POST /api/reviews/schedule` and `GET /api/reviews/due` (CORS, auth)
- Spaced-repetition rule (simple: `next_review_at = now + 2^successes days` capped, or FSRS-lite copy later)
- Background job type `REVIEW_MATERIALIZE` (optional; start with on-demand query over `user_concepts.next_review_at`)

### F4. Exercises / Quiz system
- Structured question schemas (MCQ, multiple-select, ordering, fill-in; matching/worked-math later) — JSONB payloads per type, answers not exposed pre-submit
- `POST /api/concepts/{id}/quiz` (generate via LLM, cache; Pydantic+rules validation)
- `POST /api/quizzes/{id}/attempts` (grade server-side) — returns score + rationale + next_review hint

### F5. Recommendations
- Deterministic final ranking (no LLM as ranker): `S(v) = w_g·G + w_i·I + w_c·C + w_r·R + w_n·N - w_m·M` with configurable weights + factor logging (`recommendation_factors`)
- Candidate generation may use LLM; ranking is DB-deterministic
- `GET /api/recommendations` (top 5 next concepts) — wiring to Discovery + Brain

### F6. Frontend
- Concept page: Quiz panel under the lesson (start/answer/retry, mastery bar animates on submit)
- Review page: `app/app/review/page.tsx` (due queue → question → feedback → completion summary) + `Review queue` sidebar entry (undim)
- Overview/Brain: recommendations strip + "review due" badge

### Risks
- Quiz generation rate limits (reuse free-model pool + caching by `question_hash`)
- Embedding drift (concept vs chunk spaces) — keep 768-dim consistent, validate `model: gemini-embedding-001`

---

### Phase F sub-phase status — 2026-08-27
- **F2a Review transition:** quiz answers and manual reviews now share one deterministic mastery/scheduling transition; the due-review path no longer fails on an undefined previous score.
- **F2b Review-due state:** elapsed schedules are marked `REVIEW_DUE` without changing mastery; submitting the review returns to the score-derived state. Migration `0008_review_due_state` adds the durable enum value, and review responses now expose the state.
- **F4a Quiz contract:** quiz attempts are accepted at the roadmap path `POST /api/quizzes/{id}/attempts`; `/answer` remains as a compatibility alias. Confidence is persisted with each review.
- **F5a Deterministic ranking:** recommendations now rank only from goal, interest, prerequisite readiness, recency, neighborhood, and mastery factors. LLM output no longer changes the final order.
- **F5b Outcome measurement:** recommendation evaluation now counts mastery changes only for reviews at or after the first click on that concept, excluding pre-click history.
- **F6a Review session:** the Review page now runs one due concept at a time through the existing quiz and attempt APIs, exposes rationale/next-review feedback, advances through the captured queue, and shows a completion state.
- **Checks:** focused review/recommendation tests `4 passed`; Ruff clean; non-DB API tests `61 passed`; full app-client tests remain blocked by the existing TestClient starting the real Postgres worker from the root `.env`.
- **Checks updated:** the new browser-side session test passes with Node’s built-in runner; the Review page transpiles cleanly. `npm run typecheck` remains unavailable in WSL1 and direct `tsc` exceeds the local timeout.
- **F7a Integration coverage:** added learning-loop and portrait persistence tests covering quiz generation, review scheduling, brain mastery, recommendation factors, snapshot creation, Discovery parity, and non-structural refresh reuse. The fixture checks database writability before auth-table DDL and skips managed/non-disposable databases safely.
- **Checks updated:** non-DB API tests `81 passed`; focused review tests `3 passed`; the integration module reports `10 skipped` without `DATABASE_URL`; Python compilation, full-repo Ruff, and Alembic offline SQL through `0008_review_due_state` are clean. A configured managed Supabase run previously failed on protected `auth` schema permissions, so it was not retried against shared data.
- **Next sub-phase:** the CI job now applies the head migrations and runs `test_brain_api.py` against disposable Postgres/pgvector; after that run, review calibration and the remaining responsive/E2E work.

### F6b Brain next-action slice — 2026-08-28
- **Surface:** Brain now shows a compact, horizontally scrollable next-action strip: due reviews take priority; when none are due, the first three deterministic recommendations are shown.
- **Telemetry:** recommendation links reuse the existing click endpoint, so Brain navigation contributes to recommendation evaluation alongside Overview navigation.
- **Checks:** the browser-independent Brain prompt regression passes; all five focused web checks and direct TypeScript pass. Browser interaction and responsive screenshots remain external gates.

### F5b Recommendation-outcome slice — 2026-08-28
- **Measurement:** `clicked_mastery_delta` now uses each concept's first recommendation click as its lower time boundary, preventing earlier reviews from inflating the outcome metric.
- **Checks:** the timestamp-boundary regression passes; full available non-DB API verification is `107 passed`, with Ruff and Python compilation clean.

### Phase 1d CI environment slice — 2026-08-28
- **Dependency install:** the API workflow now installs the test tools explicitly with pip (`pytest`, `pytest-asyncio`, and `ruff`). The project keeps these under PEP 735 `dependency-groups`, which pip does not install through the unsupported `.[dev]` extra syntax.
- **Checks:** workflow YAML parses and the dependency-group/workflow command alignment check passes. The disposable Postgres/pgvector run remains the authoritative integration gate.

### Phase 1 sub-phase status — 2026-08-27
- **1a Deterministic portrait inputs:** portrait input hashes now include concept labels/domains, edge direction/type/confidence, active goals, and algorithm/config versions. Edge fields remain ordered so prerequisite direction cannot be lost.
- **1b Evidence gates:** concept creation/enrollment alone no longer counts as recent learning activity; one review attempt is counted once; portraits stay sparse until 10 meaningful interactions; recency at the current instant is handled correctly. This keeps sparse/new portraits from inventing identity, Emerging Threads, or Frontiers.
- **1c Snapshot discipline:** classification additions/removals produce evolution changes; insignificant input drift reuses the current snapshot, while algorithm/config version changes still create a new one.
- **1d Golden fixtures:** deterministic A–E fixtures now cover sparse/new, mathematics specialist, cross-domain Bridge, emerging Formal Methods, and dormant Graph Theory behavior against the real portrait builder. The integration module also covers the full sparse-to-emerging snapshot flow and Discovery parity.
- **1e Debug tooling:** authenticated development-only `/api/portrait/debug` reports the exact factor contributions, selection thresholds, evidence suppression, and visual ranking factors without mutating snapshots or exposing the report in production.
- **1f Configurable scoring profile:** portrait thresholds, normalization targets, and scoring weights now live in a typed `PortraitConfig`; the active profile is included in input hashes so tuning produces a new immutable snapshot. The default profile preserves the existing scoring behavior.
- **Checks:** portrait scoring tests `17 passed`; golden portrait tests `5 passed`; portrait service Ruff clean. The next verification is the learning-loop/portrait integration suite against disposable Postgres/pgvector.

### Phase 2 sub-phase status — 2026-08-27
- **2a Anonymous form and accessible text:** the Profile uses a non-identifying human silhouette by default and exposes anchors, bridges, frontiers, emerging threads, and dormant threads in a visible textual portrait index.
- **2b Deterministic composition:** stable concept-derived layout helpers now live in a browser-safe module, with keyboard-selectable SVG regions and identifier-anchored positions that survive sibling insertion/reordering. The SVG is exposed as an accessible group with visible keyboard focus cues so its region buttons remain discoverable; the textual portrait index remains the complete equivalent. Portrait visual-source selection and inspector types are narrowed correctly.
- **2c Product boundary:** no user-photo URL, upload, or storage path is part of the core portrait. The renderer stays anonymous; sourced imagery is handled by Phase 3, and generated artwork remains deferred to Phase 6.
- **2c Responsive foundation:** Profile uses a side inspector from large tablets upward, a sticky bottom inspector below that breakpoint, and hides the caption plus secondary visual regions below 640px while preserving the human form, primary touch regions, and full textual index. Screenshot/E2E coverage remains a separate verification task.
- **Checks:** focused web tests `4 passed`; direct TypeScript typecheck passes; API non-DB tests `77 passed`. The removed photo-settings path has no remaining callers.

### Phase 3 sub-phase status — 2026-08-27
- **3a Provider and rights gates:** Wikimedia Commons metadata is retained with provider, canonical source, license, creator, dimensions, and rights class; unknown/restricted candidates are rejected before composition.
- **3b Ranking, deduplication, and caching:** visual ranking is deterministic across relevance, aesthetic fit, rights, and quality, with canonical-URL and image-URL deduplication before the limit is applied. Rights-cleared image bytes are fetched with an 8 MB cap, stored by SHA-256 through the existing object-storage protocol, and exposed through a scoped cached-image URL.
- **3b Async refresh:** visual search and image caching now run through the durable `PORTRAIT_VISUAL_REFRESH` Postgres job; requests are deduplicated by user and snapshot, the API returns `202` with a job ID, and the web client polls for the completed portrait.
- **3c Attribution and inspection:** selected visual regions expose provider, rights, creator, institution, date, attribution, and provenance links in the Profile inspector without covering the artwork with labels; their accessible labels also announce the represented concept, source title, and rights class.
- **3d Institutional fallback:** The Metropolitan Museum of Art Open Access API is queried only when Wikimedia yields fewer than two candidates; public-domain metadata and HTTPS image URLs are checked before candidates enter the shared ranking/cache path. The API source is documented in [component provenance](component-provenance.md).
- **Checks:** visual-source tests `9 passed`; targeted Ruff, full-repo Ruff, and the focused web tests remain clean. Alembic offline SQL includes migration `0007_portrait_visual_refresh_job`. Broader provider expansion and cached derivative generation remain deferred until production usage justifies them.

### Phase 5 sub-phase status — 2026-08-27
- **5a Snapshot comparison:** Discovery history cards are now keyboard-selectable and show the selected snapshot’s version, narrative, and recorded changes. The existing immutable snapshot IDs remain the selection boundary.
- **5b Timeline UI:** history is presented as a responsive vertical timeline with version markers, mastered/domain counts, and a selected-snapshot detail panel.
- **5c1 Continuity motion:** keyed SVG regions now enter and leave through `AnimatePresence` while identifier-derived positions preserve established landmarks between portrait refreshes and snapshot changes; category-qualified keys prevent collisions when a concept appears in multiple region types, and visual-source regions use the same transition boundary.
- **5c2 Reduced motion:** `useReducedMotion()` switches the region transition to zero duration without changing content, keyboard targets, or region ordering; the existing global reduced-motion CSS remains in place for CSS effects.
- **Checks:** focused web history/layout/review tests `3 passed`; direct TypeScript typecheck passes.

### Phase 4 sub-phase status — 2026-08-27
- **4b Discovery/Brain parity:** Discovery uses the same Portrait Model and now makes every surfaced node or thread actionable: nodes open their concept, threads open their first associated concept, and empty threads fall back to the Brain.
- **4c1 Failure handling:** portrait computation now rolls back the active database transaction before loading the previous immutable snapshot, so fallback hydration can safely reuse the session after a failed computation. Existing visual-source failures remain isolated per asset and preserve the current portrait.
- **4c1 Renderer fallback:** the Profile isolates artwork failures behind `PortraitErrorBoundary`; the accessible textual portrait index remains available when the SVG renderer fails.
- **4c1 Refresh feedback:** Profile and Discovery now report failed portrait/visual refreshes inline while explicitly preserving the last successful reading.
- **4c1 Image fallback:** a missing cached image now falls back to its fetched source URL at the SVG region boundary.
- **4c1 Image failure state:** if both the cached and fetched source URLs fail, the visual region keeps its data-bound frame and shows a readable source-unavailable state.
- **4c2 Async visual refresh:** Profile starts a durable user/snapshot-deduplicated visual-refresh job and keeps the last successful portrait until the worker completes; failed jobs surface the existing inline error without replacing the portrait.
- **4c3 Inspector navigation:** visual regions expose provenance, their first associated concept, and Brain navigation; thread regions expose their first associated concept as “Explore thread” plus Brain navigation.
- **4c3 Responsive foundation:** the Profile layout adapts inspector placement at the same `lg` breakpoint that creates the side-by-side layout, and reduces decorative captioning for narrow viewports without changing the underlying portrait data.
- **4c4 First-user feedback boundary:** Discovery portrait feedback now calls the shared `ensure_profile` path before writing `PortraitFeedback`, so a new authenticated user can use “Useful” or “Not me” without a profile foreign-key failure.
- **4d Privacy-safe analytics:** portrait events persist only the event type plus snapshot/element identifiers; Profile, Discovery, visual regions, refreshes, navigation, hover, and history selection are wired. No concept text or photo telemetry is sent.
- **4e1 Async portrait recomputation:** Profile and Discovery read the latest persisted snapshot; `POST /api/portrait/refresh` queues `PORTRAIT_REFRESH`, and the authenticated status endpoint returns the completed snapshot while preserving the previous one during work or failure. Recompute failures now remain `FAILED` instead of being mislabeled as successful fallback reads.
- **4e2 Refresh idempotency:** portrait refresh jobs now deduplicate by authenticated user through the durable queue, while terminal jobs release their key so a later refresh remains possible.
- **4c5 Log de-duplication:** Uvicorn and `uvicorn.error` records now stop after their shared JSON handler, preventing duplicate startup/error lines while application access logs continue through the root logger.
- **4c6 Request error boundary:** unhandled request exceptions are logged with request ID and 500 timing before the original exception is re-raised, avoiding a masking `UnboundLocalError`.
- **4c7 Source failure feedback:** the Library now surfaces the latest source-ingest job error (including upstream `403` and provider `429` details) without changing the durable source record or retry behavior.
- **4c8 Browser contract:** Playwright covers Profile keyboard activation/inspector navigation and Discovery’s shared portrait facts/history selection with mocked API responses; the test-only auth bypass is unavailable in production. Chromium execution is wired into CI, while local WSL1 browser execution remains environment-blocked.
- **Checks:** portrait fallback regression passes; full API, focused web, TypeScript, compilation, and full-repo Ruff checks remain clean. The local production-build probe is environment-blocked by WSL1/missing optional SWC. Browser contract execution is wired for CI; responsive screenshot baselines remain.

### Roadmap alignment audit — 2026-08-27
- **On track:** Phases F, 1a–f, 2a–b, 3a–d, 4b, 4c1–8, 4d, 4e1–2, and 5a–c have corresponding code and focused checks.
- **Intentional deferrals:** user-photo mode is excluded from the core product; broader provider expansion beyond Wikimedia + The Met, cached derivative generation, responsive visual regression baselines, CI browser execution, and Phase 6 generated-art editions remain open roadmap work.
- **Next:** execute the updated CI integration job against disposable Postgres/pgvector, then add browser screenshot baselines and finish responsive visual regression before advanced art.

### Roadmap and verification recheck — 2026-08-27
- **Confirmed alignment:** the implementation matches the split phases in `docs/FUTURE_STEPS.md`: F, 1a–f, 2a–b, 3a–d, 4b, 4c1–8, 4d, 4e1–2, and 5a–c have code plus focused checks.
- **Scope confirmed:** no portrait-photo upload/storage path exists in the core implementation; visual assets are fetched, rights-gated, cached where permitted, and attributed. Generated art remains deferred to Phase 6.
- **Fresh evidence:** full-repo Ruff passed; non-DB API `84 passed`; portrait/visual/golden `24 passed`; web `3 passed`; direct TypeScript and Python compilation passed; Alembic offline SQL through `0009_portrait_events` passed; Brain stale-hover regression is covered by the compiled TypeScript test; DB integration remains `11 skipped` locally pending disposable Postgres/pgvector.
- **Next slice:** execute the updated CI integration job in disposable Postgres/pgvector, then close responsive visual regression, browser E2E, and final Phase 4 release polish. Do not start Phase 6 art before those gates.

### Phase 4c release-polish slice — 2026-08-27
- **Responsive breakpoint:** the inspector is side-by-side at `lg` and sticky-bottom only below `lg`, matching the documented desktop/tablet/mobile layout intent.
- **Asset resilience:** visual regions now fall back from cached bytes to the fetched source URL, then to a readable non-image state if both fail.
- **Interaction parity:** Profile inspector actions now cover provenance, related concept/thread, and Brain navigation for the selected portrait element.
- **Checks:** direct TypeScript, focused web tests (`3 passed`), full-repo Ruff, and the existing API suites remain clean. Browser screenshots still require a browser runner; no Playwright dependency was added to the local checkout.

### Phase 3b/4c async visual-refresh slice — 2026-08-27
- **Durable work:** added migration `0007_portrait_visual_refresh_job`, worker handler registration, authenticated job-status polling, and client-side completion handling.
- **Failure isolation:** provider and cache failures remain contained at the asset boundary; the last successful portrait remains available while refresh work is pending or failed.
- **Checks:** visual-source tests (`7 passed`), full non-DB API suite (`79 passed`), Alembic offline SQL, full Ruff, and direct TypeScript all pass.

### Phase F2b review-due slice — 2026-08-27
- **Durable state:** added `REVIEW_DUE` to the mastery enum and migration `0008_review_due_state`.
- **Scheduler behavior:** the due queue marks elapsed schedules as due; review submission clears the due state through the shared deterministic transition.
- **Checks:** focused review tests (`3 passed`), full non-DB API suite (`81 passed`), Alembic offline SQL, Ruff, Python compilation, and direct TypeScript all pass.

### Integration migration/telemetry slice — 2026-08-27
- **Migration gate:** CI now creates the minimal `auth.users`/`auth.uid()` Supabase stub, applies `alembic upgrade head` to its pgvector service, then runs the integration suite. This catches migration drift that metadata-only `create_all` cannot catch.
- **Telemetry smoke:** the integration module now posts a real `portrait_viewed` event for a new user; the route mirrors the profile before inserting the FK-backed event.
- **Checks:** portrait analytics unit tests `3 passed`; non-DB API `86 passed`; integration module `11 skipped` locally without `DATABASE_URL`; CI is the authoritative disposable-Postgres run.

### Source-ingestion deployment-reliability slice — 2026-08-27
- **Worker failure boundary:** job type, ID, and payload are snapshotted before rollback; upstream/embedding failures can now be persisted without triggering SQLAlchemy `MissingGreenlet` from expired ORM attributes. Failed source jobs update their source status, while retryable jobs retain the existing backoff.
- **Remote PDFs:** URL-backed PDFs now use the already-installed `pypdf` parser, sharing the extraction path with stored uploads. The old dependency error was a code-path rejection, not a missing package.
- **Render evidence:** build/startup and `/api/health` succeeded. ACM, Wikipedia, CHOP, PubMed, and World Scientific returned upstream `403`; Gemini embeddings returned `429 RESOURCE_EXHAUSTED`. Those remain provider/source-access constraints, but they are now contained by the job boundary instead of crashing the worker.
- **Checks:** the new runner/PDF regression tests pass (`3 passed`); non-DB API suite is `87 passed`; Ruff and Python compilation pass. Web TypeScript passes, the compiled Brain regression passes (`2 passed`), and the focused JavaScript checks pass (`3 passed`).

### Uvicorn log de-duplication slice — 2026-08-27
- **Observed issue:** Uvicorn startup/error records propagated through both its own JSON handler and the root handler, producing duplicate structured lines in Render logs.
- **Fix:** Uvicorn and `uvicorn.error` now stop propagation after the shared JSON handler; access records continue through the application root logger.
- **Checks:** focused logging/worker/source/portrait suite passes (`18 passed`); full non-DB API suite passes (`104 passed`); the Render source/embedding failures remain the separate redeploy and provider-quota gates above. The local disposable Postgres gate remains unrun because the Docker daemon is unavailable.

### Request error-boundary logging slice — 2026-08-27
- **Observed issue:** an unhandled request exception left `response` unset in `RequestContextMiddleware`, so the access log could raise `UnboundLocalError` and hide the original failure.
- **Fix:** middleware now logs the request ID and 500 timing, then re-raises the original exception.
- **Checks:** middleware regression passes; full API verification remains the same apart from the added test.

### Source-ingest stage-fidelity slice — 2026-08-27
- **Observed issue:** the source library exposed a `FETCHED` state, but URL and object-storage ingestion skipped it and reported only after extraction.
- **Fix:** successful remote, stored-byte, and inline-note reads now mark the source `FETCHED` before parsing/conversion; extraction, chunking, and embedding retain their existing transitions.
- **Checks:** focused source/worker/middleware/logging tests pass (`4 passed`); full available non-DB API suite passes (`106 passed`), with Ruff and Python compilation clean.

### CI migration-gate slice — 2026-08-27
- **Observed issue:** the migration sanity step piped Alembic output into `test -s /dev/stdin`, which closed the producer early and reproduced `BrokenPipeError` locally.
- **Fix:** the workflow now writes generated SQL to `$RUNNER_TEMP/lattice-alembic.sql` and checks the completed file, preserving the full Alembic process output.
- **Checks:** the replacement command generated all migrations through `0010_portrait_refresh_job` locally; disposable Postgres execution remains a CI-only gate because the local Docker daemon is unavailable.

### Source failure-feedback slice — 2026-08-27
- **Observed issue:** failed source rows showed only a generic `Failed` badge even though the worker had already persisted the actionable upstream/provider error.
- **Fix:** the Library response includes the newest source-ingest error via one batched job lookup; the web row renders it inline for both terminal failures and retrying jobs.
- **Checks:** the source output regression preserves the error field; the full non-DB API suite (`106 passed`), TypeScript, Ruff, and compilation remain clean.

### Focused-island label regression slice — 2026-08-27
- **Root cause:** a concept selected in the overview stayed selected when an island was opened; the focused reducer then faded every non-neighbor label.
- **Fix:** focused mode now uses only a valid live hover as its label-fading anchor, while preserving normal selection behavior in the overview.
- **Checks:** compiled Brain regression tests pass (`3 passed`), web TypeScript passes, focused JavaScript checks pass (`3 passed`), API non-DB suite passes (`87 passed`), Ruff and Python compilation pass.

### Service-root release-polish slice — 2026-08-27
- **Host surface:** `/` now returns a small JSON service/status response and points to `/api/health`; Render’s root probe no longer receives a misleading 404.
- **Checks:** root-route regression passes (`1 passed`); the broader API, Ruff, Python compilation, web TypeScript, and focused web checks remain clean.

### Developer portrait-debug slice — 2026-08-27
- **Read-only tooling:** development-only `GET /api/portrait/debug` exposes the exact deterministic factor contributions and selection thresholds for portrait classifications, plus the four visual ranking factors.
- **Safety boundary:** the endpoint requires the normal authenticated user and returns 404 in production; it does not create or mutate a snapshot.
- **Checks:** debug endpoint and scoring tests pass (`2 passed`); non-DB API suite is `89 passed`; Ruff, Python compilation, web TypeScript, and focused web checks remain clean.

### Institutional visual-provider fallback slice — 2026-08-27
- **Fallback:** added The Met public-domain adapter and invoke it only when Wikimedia returns fewer than two ranked candidates, preserving the existing ranking, rights, cache, and attribution boundary.
- **Rights boundary:** candidates require The Met's `isPublicDomain` flag, a title, and an HTTPS image URL; no user image is uploaded and no generated image is introduced.
- **Checks:** visual-source tests `9 passed`; full non-DB API suite `91 passed`; Ruff, Python compilation, web TypeScript, and focused web checks remain clean. Browser visual regression and production-provider verification remain deployment gates.

### Stable portrait-layout slice — 2026-08-27
- **Stability:** concept, thread, and visual-source positions now derive from their identifiers rather than sibling index/count, so existing regions retain their positions as a portrait changes.
- **Checks:** the layout regression passes; focused web tests are now `4 passed`, and direct TypeScript remains clean.

### Portrait accessibility slice — 2026-08-27
- **Semantics:** changed the interactive portrait SVG from image-only semantics to an accessible group, preserving keyboard-focusable region buttons and the textual portrait index; added visible focus rings for concept and visual-source regions.
- **Checks:** the accessibility regression passes; browser assistive-technology verification remains an external gate.

### Responsive portrait slice — 2026-08-27
- **Mobile policy:** below 640px, CSS hides secondary bridges, frontiers, threads, orbit decoration, and visual sources; primary regions, the human form, and the complete textual index remain available.
- **Checks:** responsive source regression, focused web tests, and TypeScript pass; browser screenshot verification remains an external gate.

### Visual-source accessibility slice — 2026-08-27
- **Semantics:** visual regions now announce the represented concept, source title, and rights class to assistive technology while retaining the visual inspector for full provenance.
- **Checks:** the accessibility regression passes; browser screen-reader verification remains an external gate.

### Async portrait-recompute slice — 2026-08-27
- **Durable work:** added migration `0010_portrait_refresh_job`, worker registration, and authenticated `GET /api/portrait/refresh/{job_id}` polling for `PORTRAIT_REFRESH`.
- **Read path:** Profile and Discovery serve the latest valid persisted snapshot; both surfaces expose the refresh control, refresh work runs outside the request, the web hook updates the portrait only after success, and failed recomputation preserves the last valid snapshot without reporting false success.
- **Checks:** API non-DB suite `99 passed`; focused visual/portrait suite `33 passed`; Ruff, Python compilation, offline Alembic SQL through `0010`, direct TypeScript, compiled Brain checks (`3 passed`), and focused JavaScript checks pass. Integration still requires disposable Postgres/pgvector; browser E2E remains external.
- **CI alignment:** the web CI job now runs these browser-independent portrait/layout/Brain regressions before its production build; no browser package or image-upload path was added.

### Private cached-visual transport slice — 2026-08-27
- **Privacy boundary:** cached visual bytes now verify the authenticated snapshot owner; the Profile renderer loads them with the bearer token and uses the public rights-cleared source URL as fallback.
- **Checks:** owner-scope regression, portrait accessibility regression, and direct TypeScript checks pass; browser screenshot and cross-origin runtime verification remain external.

### Open-access source handoff slice — 2026-08-27
- **Ingestion URL:** OpenAlex results now prefer an HTTPS open-access PDF, then an HTTPS open-access landing page, before falling back to the existing primary/publisher or DOI URL. DOI and arXiv identifiers remain unchanged for deduplication.
- **Checks:** provider regression and full API non-DB suite (`99 passed`) pass; blocked publisher URLs still require permitted alternatives or an external provider/API.

### Portrait transition key-isolation slice — 2026-08-27
- **Transition identity:** anchor, frontier, emerging-thread, and visual-source regions now use category-qualified React keys, so repeated concept/source IDs cannot collide inside the shared `AnimatePresence` boundary.
- **Checks:** the accessibility/key regression passes; direct TypeScript and the focused web checks remain clean.

### First-user portrait feedback slice — 2026-08-27
- **Write boundary:** Discovery feedback now mirrors the authenticated user into `profiles` before inserting the FK-backed feedback row, reusing the existing profile-initialization helper.
- **Checks:** focused portrait/worker/provider/visual tests pass (`23 passed`); Ruff and Python compilation pass.

### Durable visual-refresh dedupe slice — 2026-08-27
- **Idempotency:** active visual refreshes now deduplicate by authenticated user and snapshot; terminal jobs release their unique key while retaining history, allowing a later refresh without multiplying provider requests or permanently blocking the button.
- **Checks:** affected API tests pass (`26 passed`); the non-DB API suite excluding the local TestClient hang passes (`102 passed`); Ruff and Python compilation pass.

### Race-safe portrait-refresh slice — 2026-08-27
- **Idempotency:** portrait recomputation now uses a user-scoped durable dedupe key instead of scanning an arbitrary 20 active jobs, so concurrent requests share one job and terminal history does not block future refreshes.
- **Checks:** the refresh route regressions and non-DB API suite pass (`102 passed`); Ruff and Python compilation pass.

### Portrait rendering decision slice — 2026-08-27
- **Decision:** documented SVG as the canonical semantic portrait renderer and Sigma/WebGL as the separate Brain renderer in [portrait-rendering.md](portrait-rendering.md).
- **Boundary:** the document records identifier-anchored stability, CSS mobile simplification, reduced-motion behavior, cached/source image fallback, and the no-upload/no-generated-art canonical boundary.
- **Checks:** documentation is aligned with the existing focused web and TypeScript checks; browser screenshot and assistive-technology verification remain external gates.

## 7. How to Run (first-time & every-session)

### Env
- **Root** `D:\fun stuff\lattice\.env` — keep real values local only; API reads it via `parents[4]`
  ```
  SUPABASE_URL=replace_me
  SUPABASE_ANON_KEY=replace_me
  SUPABASE_SERVICE_ROLE_KEY=replace_me
  DATABASE_URL=replace_me
  GOOGLE_API_KEY=replace_me
  TAVILY_API_KEY=replace_me
  OPENROUTER_API_KEY=replace_me
  OPENROUTER_MODEL=z-ai/glm-5.2:free
  WEB_ORIGIN=http://localhost:3000
  ENVIRONMENT=development
  LOG_LEVEL=INFO
  ```
- **Web** `apps/web/.env.local` — keep real values local only
  ```
  NEXT_PUBLIC_SUPABASE_URL=replace_me
  NEXT_PUBLIC_SUPABASE_ANON_KEY=replace_me
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

### First time
```powershell
# DB (one-time): create pgvector + run migrations
cd "D:\fun stuff\lattice\apps\api"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\alembic.exe upgrade head   # expect 0001_baseline → 0002_job_timestamps

# Supabase console (one-time): SQL Editor → CREATE EXTENSION IF NOT EXISTS vector; (if alembic didn't)
# Auth: Authentication → Providers → Google (paste Client ID/Secret, add http://localhost:3000/auth/callback)
# Auth → URL Configuration → Site URL http://localhost:3000 ; Redirect URLs .../auth/callback

# Web
cd "..\web"
npm install
npm run dev
```

### Every session
```powershell
# Terminal 1 — backend (keep alive)
cd "D:\fun stuff\lattice\apps\api"
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
# Health: http://localhost:8000/api/health  (reports openrouter/... vs gemini, embeddings, web_search, academic)
# Docs:   http://localhost:8000/docs

# Terminal 2 — frontend
cd "D:\fun stuff\lattice\apps\web"
npm run dev   # http://localhost:3000 ; Ctrl+Shift+R after deploy
```

---

## 8. Troubleshooting Log (what broke, what fixed, what to watch)

| Symptom | Cause | Fix | Watch |
|---------|-------|-----|-------|
| `DATABASE_URL` "unused" / `InvalidPasswordError` for `postgres` not `postgres.bkql...` | `Settings` looked for `.env` at CWD `apps/api/.env` (missing) → fell back to `postgres:postgres@localhost` | `parents[4]` absolute resolution | Always keep `.env` at repo root |
| `alembic upgrade` → `TSVECTOR NullType` | `name_tsv` was a generated column but mapped as plain `TSVECTOR` → ORM included `NULL` in INSERT | `Computed("to_tsvector('english',coalesce(canonical_name,''))", persisted=True)` on the model; explicit `pg.TSVECTOR()` in migration | Any new generated column must use `Computed` on the model |
| `FK user_concepts_user_id_profiles` | `profiles` mirror only created by `/users/me`, not by concept/pathway/source creation | `ensure_profile` made idempotent `(user_id,email)` and called by every user-owned write + inside `ensure_user_concept`; `Ambiguous` → strip to `Computed`/enum name | New user-owned tables must call it |
| `Computed name 'Computed' is not defined` / `hydrated` class mismatch on `<html>` | Reload race (edit half-applied) + browser extension mutating `className` | Imported `Computed`; added `suppressHydrationWarning` on `<html>`; full imports | Don't rely on partial hot-reloads for import fixes |
| `ANIMATION` "Template"/flicker → `animate-pulse` everywhere + CSS blur aurora + multi-WebGL contexts | `blur(110px)` 60vw + 2× WebGL canvases (sidebar+page) + Sigma | Single shader `NebulaSky` (fbm+stars+parallax, `dpr [1,1.5]`), sidebar → CSS gradients, all `animate-pulse` → `Shimmer` brass sweep, `AnimatePresence mode="wait"` → overlapping crossfade | If flicker returns, look for added WebGL contexts or `animate-pulse`; report the route |
| Supabase: project URL "missing" / DB password reset "not there" | New dashboard moved it to `Database → Settings` (not Settings gear) | Direct URL `https://supabase.com/dashboard/project/bkql.../database/settings` | Avoid `ALTER ROLE postgres` in SQL editor (needs superuser); use Dashboard reset |
| Gemini model retirements (`gemini-2.0-flash`, `text-embedding-004`) | Google rotated models for API version `v1beta` | `gemini_model: gemini-2.5-flash`, `gemini_embedding_model: gemini-embedding-001` (768-dim), embedding list check verified `gemini-embedding-001/2` support `embedContent` | Treat model names as config, not code constants |
| OpenRouter 429s | Free tier per-minute rate limits | Pool cycling `GLM-5.2 → Ultra 550B → Super 120B → MiniMax M3`, sticky ` _current`, 90s backoff on 429; nearly every job succeeded on 2nd attempt | Monitor `httpx` logs `POST openrouter ... 429 → 200 OK` on next model |
| Brain "all points same spot" | `x:0,y:0` for all nodes → FA2 zero repulsion | Golden-angle spiral seeding + Louvain ring + enforcement `minSep` + degenerate guard | If graph too sparse, Louvain → 1 community → domain fallback triggers |
| "No connecting lines" | Default edge `0.06` alpha invisible | `0.30` default, `0.95`+thick on hover, `EdgeCurveProgram` | Tune in `BrainCanvas` edge default |
| "FV inside ML" / clusters too close | Ring only by `domain` label; FV's domain was ML | Louvain communities (`graphology-communities-louvain`, `resolution 1.1`), size-aware radii (`√share`), per-pair repulsion, gravity `0.32` | Requires a real edge (bridge); generate a pathway after the bridge fix so `FV ↔ Category Theory` materializes |
| `.next` corruption `vendor-chunks/motion.js` / `routes-manifest.json` | Running `npm run build` from WSL while Windows dev lived on same `.next` | Stop dev before builds; dev uses `typecheck` only; WSL `rm -rf .next` fix | Rule: never build while dev is live on the other OS mount |
| Lesson 404 embedding + 502 discovery | See above: embedding model + OpenAlex `mailto` + arXiv `http` + `RankedCandidate` float/str + lesson route catching | All fixed: embedding `001`, OpenAlex sanitizes `?` punctuation and drops `mailto`, arXiv `https+follow_redirects`, `factors: dict[str,Any]`, lesson error → `AppError` 502 | Discovery is now: Tavily `POST` 200, arXiv `https` 200, OpenAlex 200 |
| `intuition` crash on concept page | Old hook cached 202 response as lesson + model typo `keheading` → validation failure | Guard `lesson.data?.content?.intuition`, `Shimmer` + post-persisted larger lesson (`a3d65c89…` GROUNDED) already in DB; `_coerce_payload` fuzzy snap at 0.8 + `output_tokens` bump; add `select` not needed | Hard-refresh after deploy; if crash persists, paste new stack line (old one was `:226:70` inside `ConceptPage`) |
| Render worker `MissingGreenlet` after a source/embedding error | `rollback()` expires the merged `Job`; the exception path then read `attached.type`, `attached.payload`, or `attached.id` outside SQLAlchemy's async greenlet | Snapshot primitive job metadata before rollback and use those snapshots for failure bookkeeping/logging; add runner regression coverage | Redeploy and confirm failed jobs become `FAILED`/backoff `PENDING`, never stranded `RUNNING` |
| Source ingestion gets repeated `403` responses | Publisher/reference sites block server-side bot requests or the Render egress IP; `response.raise_for_status()` correctly surfaces the upstream denial | Treat as source-access/provider constraints; prefer permitted/API-backed source URLs and let the durable job record the failure | Do not interpret a `403` as a missing Python dependency |
| Remote PDF says parser dependency is missing | The URL branch rejected every `application/pdf` response before invoking `pypdf`; Render did install `pypdf` | Shared `extract_pdf()` path now handles URL and object-storage bytes | Test one public PDF and one uploaded PDF after redeploy |
| Gemini embedding `429 RESOURCE_EXHAUSTED` | Google API quota/billing limit was exceeded; this is independent of Render startup | Existing 90-second retry/backoff contains the job; restore quota/billing or configure an available embedding provider before bulk ingestion | Avoid bulk re-ingestion while the quota is exhausted |
| Render primary URL returns `HEAD / -> 404` | The API had no root route; the service health endpoint is `/api/health` | Root now returns service/status metadata and points to `/api/health` | Redeploy and confirm the Render probe sees 200 |

---

## 9. File Map (where things live)

```
lattice/
├── .env                        # root — API source of truth
├── .env.example
├── README.md
├── docs/
│   ├── architecture.md
│   ├── component-provenance.md
│   ├── data-model.md           # if present
│   └── HANDOFF.md              # ← this file
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/0001_baseline.py, 0002_job_timestamps.py
│   │   └── app/
│   │       ├── main.py (+ lifespan → init_engine + start_worker)
│   │       ├── api.py (router aggregation)
│   │       ├── core/{config,auth,errors,logging}.py
│   │       ├── db/{base,session}.py + models/{concept,learning,source,lesson,job,user}.py
│   │       ├── domain/graph.py
│   │       ├── jobs/{queue,runner,handlers}.py
│   │       └── modules/{brain,concepts,pathways,sources,retrieval,lessons,health,users}/
│   └── web/
│       ├── package.json (+ three, @react-three/fiber, @sigma/edge-curve, framer/motion, graphology)
│       ├── .env.local (NEXT_PUBLIC_*)
│       ├── app/
│       │   ├── layout.tsx (Spectral/Hanken/Plex Mono + suppressHydrationWarning)
│       │   ├── globals.css (Observatory tokens: ink/chart/parchment/brass + .eyebrow/.atlas-title/.graticule)
│       │   ├── login/page.tsx (NebulaSky + ShimmerText)
│       │   ├── app/
│       │   │   ├── page.tsx (Overview: NebulaSky, SpotlightCard+BorderBeam, CountUp)
│       │   │   ├── layout.tsx, providers.tsx
│       │   │   ├── brain/page.tsx (graph/list toggle, Fuse bar + full-screen fusing overlay)
│       │   │   ├── pathways/page.tsx + [id]/page.tsx (NebulaSky, GeneratingState with orbit)
│       │   │   ├── library/page.tsx (NebulaSky, discover+library)
│       │   │   └── concepts/[id]/page.tsx (book-chapter renderer)
│       │   └── auth/callback/route.ts
│       ├── components/{brain,lessons,pathways,shell,sources,ui}/
│       │   └── ui/{NebulaSky,Starfield,Spotlight,Shimmer,effects}.tsx
│       ├── hooks/{useBrain,useLesson,usePathways,useSources}.ts
│       ├── types/{brain,lessons,pathways,sources}.ts
│       ├── lib/{api,utils,config,store/brain}.ts + lib/supabase/{client,server,middleware}.ts
│       └── middleware.ts (Supabase session refresh)
└── supabase/  # if used for local supabase CLI
```

---

## Latest implementation slice — 2026-08-28

- Phase 2c is now implemented: private JPEG/PNG/WebP profile-photo upload,
  replacement, deletion, explicit enable/disable, owner-scoped streaming, and
  silhouette fallback. Migrations `0011_private_portrait_photos` and
  `0012_portrait_photo_events` add the data and telemetry boundary.
- Phase 6 presentation work is now implemented: Editorial, Constellation,
  Archive, Topographic, Sigil, Botanical, Orbital, and Minimal themes plus
  source-free deterministic SVG/PNG share-card editions and summary sharing.
  Export never includes profile photos or licensed visual-source pixels.
- The source list uses one chunk-count aggregate query instead of one count per
  source. Playwright now covers four Profile/Discovery/mobile/photo scenarios;
  local execution remains blocked by this WSL1 checkout's Windows-only Next
  SWC package, while CI installs Linux dependencies.

## 10. Immediate Next Actions for You

1. **Restart backend** (or rely on `--reload` if already up) — everything above is already saved:
   ```powershell
   cd "D:\fun stuff\lattice\apps\api"
   .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
   ```
2. **Hard-refresh web:** `Ctrl+Shift+R` at `http://localhost:3000`
3. **Verify the four fixes** after refresh:
   - Brain: FV no longer in ML cluster (may need one fresh pathway generate to create the `FV ↔ Category Theory` bridge)
   - Pathways → Generate → `Charting` badge + shimmer are smooth, no pulse
   - Concept → Generate grounded lesson → orbit+ sweep (no pulse), then book sections render (check `a3d65c89…` is already there for Formal Verification)
   - Fuse: select two stars → Fuse → confirm 201 in Network, 429s cycle silently to next model
   - Profile → Find sourced visuals: confirm the request returns a visual-refresh job, the old portrait stays visible while it runs, and the completed sources appear without a full portrait recomputation
   - Profile → Portrait photo: create the private `lattice-private` Supabase bucket, upload a JPEG/PNG/WebP, toggle photo use, replace it, and delete it. The anonymous silhouette must remain when photo loading fails.
   - Profile → Edition: switch among the eight themes and download both SVG and PNG share cards. These cards intentionally exclude the profile photo and sourced image pixels.

---

*Generated for handoff. Keep this file updated with each phase — Phase F entries will append below.*
