# Lattice — Suggested Future Phases

F–H close the core loop: learn a concept, practice it, save source material, and see how the Brain is changing. The next phases should deepen that loop before adding social or billing features.

## Phase I — Better practice

- Add fill-in-the-blank, multi-select, ordering, and worked-math exercises behind the same server-side grading contract.
- Keep question generation on the OpenRouter pool, validate every payload with Pydantic, and cache by concept + lesson revision.
- Add response time and per-question difficulty calibration to the existing review log.
- Replace the simple interval rule with FSRS-lite only after review history is large enough to evaluate it.

## Phase J — Library depth

- Add OCR for scanned PDFs and a page-level citation locator for every extracted chunk.
- Move local upload storage to S3-compatible object storage with signed URLs and resumable uploads.
- Add source folders, tags, full-text search, and explicit concept links from the library UI.
- Re-ingest when a source changes and retain extraction/version metadata so old lesson citations remain auditable.

## Phase K — Recommendation quality

- Log deterministic and LLM factors with every recommendation impression and click.
- Evaluate ranking offline against review outcomes (mastery gain, completion, and source usefulness).
- Add prerequisite-aware candidates and diversity constraints so the feed does not repeat one domain.
- Keep Gemini isolated as the ranking judge; never silently reuse the generation model for ranking.

## Phase L — Portrait evolution

- Store periodic portrait snapshots instead of only calculating the current view.
- Render a timeline of mastery deltas, domain growth, bridge formation, and abandoned interests.
- Add confidence labels and an explanation for every inferred gap or bridge.
- Let the learner dismiss or correct an inference; corrections become explicit user signals.

## Phase M — Reliability and safety

- Add job retry dashboards, provider spend budgets, and alerting for stuck ingestion/generation jobs.
- Add per-user storage quotas, deletion/export controls, and source-content encryption at rest.
- Run retrieval/citation checks in CI and add browser smoke tests for quiz, upload, review, and Fuse flows.

## Deferred until the learning loop is proven

Social sharing, teams, billing, and a large plugin ecosystem add surface area without improving the single-user learning loop. Revisit them after review outcomes and source-grounded lesson quality are measurable.

## Frontend recommendations

These keep the Observatory identity while making the product faster to read and act on:

1. **Make the next action dominant.** Put one primary card at the top of Overview: “Review 3 due” or “Continue Formal Verification.” Keep health/instrument panels secondary so the page answers “what do I do now?” immediately.
2. **Keep one continuous sky.** The app shell now owns the single WebGL night-sky canvas; keep page content transparent and use `bg-surface` only for readable cards. This avoids the sidebar seam and prevents multiple canvases from fighting for GPU time.
3. **Give the Brain explicit instruments.** Add compact zoom-to-fit, reset-layout, and filter controls near the graph. Preserve the semi-chaotic graph, but let users temporarily isolate a domain or edge type without leaving the canvas.
4. **Treat lessons like a reader.** Add a thin reading-progress rail, previous/next concept controls, and a “practice this” action at the end of each chapter. Keep citations inline and never hide them behind a separate sources page.
5. **Make the library scannable.** Add type/status filters (`PDF`, `paper`, `note`, `URL`, `transcript`), a single search field, and visible ingestion progress. Use a compact list on desktop and stacked cards on mobile.
6. **Show why the system inferred something.** On Discovery, pair each bridge/gap/emerging-interest item with its evidence (“3 related edges”, “2 recent failed reviews”) and keep the Useful/Not me correction affordance close to the claim.
7. **Design mobile deliberately.** Collapse the 240px sidebar into a bottom navigation or drawer below `md`; keep the desktop sidebar sticky. Long lessons and library lists should own scrolling, not the whole shell.
8. **Protect reading performance.** Keep the shared canvas at one context, lazy-load Sigma/Brain, virtualize very long source lists, and honor reduced-motion preferences for every graph and shimmer animation.
