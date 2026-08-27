# Portrait Rendering Decision

**Status:** implemented · 2026-08-27

## Decision

The canonical Intellectual Portrait uses a single, responsive SVG renderer.
The Brain remains a separate Sigma.js/WebGL surface. CSS handles page layout,
breakpoints, and motion preferences; no additional portrait-rendering library
is needed.

## Why SVG fits the portrait

- A fixed `1000 × 760` viewBox makes deterministic composition and snapshot
  comparison straightforward.
- Native SVG paths and `clipPath` provide the anonymous human form and bounded
  internal imagery without a bitmap-processing pipeline.
- Concept, thread, and visual-source regions are DOM-addressable `<g>`
  elements with keyboard activation, accessible names, and visible focus cues.
- `<image>` supports cached-image URLs first, then fetched source URLs, with a
  readable source-unavailable state when both fail.
- Cached bytes are fetched with the current Supabase bearer token and converted
  to an object URL because SVG image requests cannot attach custom auth headers.
- The renderer only draws bounded slices of the portrait model, keeping the
  DOM small for the current single-user scale.

Canvas was rejected for the portrait because its pixels do not provide
interactive accessibility or source inspection without recreating a parallel
hit-target and text layer. WebGL was rejected because the portrait needs
semantic DOM regions and source metadata more than it needs a GPU scene.
D3 would add a data-binding layer without solving either requirement.

## Rendering boundary

```text
PortraitModel
    ↓
PortraitRenderer (SVG)
    ├── anonymous human form
    ├── concept/thread regions
    ├── fetched visual-source regions
    └── accessible textual portrait index (Profile)
```

The canonical portrait does not upload or store a user photograph and does not
generate artwork. Visual assets come through the rights-gated source service;
generated art remains a future, non-authoritative edition.

## Stability and responsive behavior

Region coordinates derive from concept, thread, or asset identifiers rather
than sibling index/count, so an existing region keeps its position when a
snapshot adds or reorders neighbors. On screens narrower than 640px, CSS hides
secondary regions and orbit decoration while retaining the human form,
primary regions, and the complete textual index.

The shared reduced-motion media rule removes transitions and animations when
the user requests reduced motion. Error boundaries preserve the textual index
if the SVG renderer fails.

## Other surfaces

The Brain uses Sigma.js/WebGL because it needs graph hit testing, camera
navigation, community layout, and label level-of-detail. It is intentionally
not reused for the portrait: the Brain is an exploratory graph, while the
Portrait is a stable, semantic composition.

## Verification and open gate

Browser-independent tests cover deterministic coordinates, sibling-independent
stability, accessible SVG semantics, visible focus cues, responsive hiding,
and the existing portrait/history flows. Direct TypeScript checking passes.
Browser screenshot, keyboard, and assistive-technology verification still
requires a browser-capable CI or development environment.
