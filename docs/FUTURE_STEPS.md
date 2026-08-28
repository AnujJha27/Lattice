# Lattice — Intellectual Portrait PRD v2

**Status:** Build-ready
**Feature:** Intellectual Portrait
**Primary surfaces:** Profile, Discovery
**Product:** Lattice
**Audience:** Codex / implementation agent
**Priority:** High
**Supersedes:** All previous Intellectual Portrait specifications

---

# 1. Product Definition

The **Intellectual Portrait** is a living visual representation of the user's intellectual identity derived from their actual activity inside Lattice.

It should represent:

* what the user knows
* what they repeatedly return to
* what domains dominate their knowledge
* what concepts bridge different domains
* what they are currently trying to understand
* what interests are emerging
* what areas have become dormant
* how their intellectual landscape is changing over time

The feature has two related manifestations:

```text
PROFILE
    ↓
Human-centered Visual Portrait
"What does my intellectual world look like?"

DISCOVERY
    ↓
Analytical Intellectual Portrait
"What is changing in my intellectual world?"
```

Both use the **same backend Portrait Model**.

Do not implement two separate inference systems.

---

# 2. Core Experience

The Profile portrait should feel like:

> an actual portrait of a person whose intellectual life has become visible around and through them.

The human element is central.

The user's knowledge should appear as:

* diagrams
* historical scientific imagery
* mathematical structures
* maps
* illustrations
* manuscripts
* schematics
* graphs
* symbolic fragments
* conceptual constellations

that are meaningfully connected to their actual Brain.

The result should sit somewhere between:

* editorial portraiture
* scientific illustration
* knowledge visualization
* collage
* cartography
* constellation
* visual biography

It must NOT feel like:

* a glowing AI brain
* cyberpunk stock art
* a personality-test result
* a random collage
* a generic profile picture
* an AI-generated fantasy character
* a dashboard pasted over someone's head

---

# 3. Product Principle

The feature succeeds when the user looks at it and thinks:

> That actually represents what I've been learning.

Not merely:

> That's a cool picture.

Every significant visual element must correspond to meaningful Portrait Model data.

---

# 4. System Architecture

```text
Lattice activity
      │
      ▼
Knowledge Graph
      │
      ▼
Portrait Analysis
      │
      ▼
Structured Portrait Model
      │
      ├──────────────► Discovery insights
      │
      ├──────────────► Human-centered portrait
      │
      └──────────────► Historical evolution
```

The LLM must not independently decide what the user's intellectual identity is.

The backend computes the structured facts first.

LLMs may only assist with:

* concise narrative rendering
* visual search-query generation
* optional pedagogical descriptions
* optional future art interpretation

---

# 5. Portrait Terminology

Use these terms consistently.

## Anchor

A concept or domain that is deeply established in the user's knowledge.

## Bridge

A concept connecting otherwise distinct clusters.

## Frontier

A concept or domain the user is actively moving toward.

## Emerging Thread

A coherent cluster showing meaningful recent growth.

## Dormant Thread

A previously important cluster with little recent activity.

## Domain

A broad intellectual area.

## Portrait Element

A visual object corresponding to one of the above structures.

## Portrait Snapshot

An immutable representation of the user's portrait at a particular time.

## Visual Source

An external image or illustration used inside the portrait.

---

# 6. Primary Surfaces

## Profile

Profile contains the full human-centered visual portrait.

Primary purpose:

> intellectual identity.

## Discovery

Discovery contains a more analytical representation.

Primary purpose:

> interpretation, change, opportunity and direction.

## Brain

Brain remains the detailed interactive graph.

Primary purpose:

> exploration.

These surfaces must remain distinct.

```text
Brain
    = everything

Portrait
    = what matters most

Discovery
    = what is changing and where to go
```

---

# 7. Profile Experience

Recommended hierarchy:

```text
YOUR INTELLECTUAL PORTRAIT

        [ HUMAN-CENTERED PORTRAIT ]

184 concepts · 5 domains · 3 active frontiers
Updated 2 days ago

"Your knowledge is currently anchored..."

Strongest Threads
Current Frontier
Bridges
Emerging Interests

Recent Evolution

[ Explore in Discovery ]
[ Open Brain ]
```

The portrait should be one of the defining pieces of the Profile experience.

Do not reduce it to a small card.

---

# 8. Human Element

The visual composition should contain a recognizable human form.

Supported modes:

## Mode A — User Photograph

If the user explicitly provides a profile photograph and explicitly enables its use:

* use that photograph as the human anchor
* preserve recognizability
* do not modify facial identity unnecessarily
* intellectual imagery may overlap, mask, surround or pass through the composition

## Mode B — Anonymous Human Form

If no photo is supplied:

use a deliberately non-identifying:

* silhouette
* profile
* bust
* abstract person form

Do NOT generate a fake realistic human supposedly representing the user.

---

# 9. No Photo Requirement

The feature must function completely without a profile photo.

Do not make the user upload:

* a selfie
* biometric information
* facial data

The human presence can remain symbolic.

---

# 10. Portrait Composition

The human figure acts as the central compositional anchor.

Knowledge-related imagery may exist:

### Inside the figure

Representing established knowledge and Anchors.

### Crossing the boundary

Representing Bridges between established knowledge and newer areas.

### Around the figure

Representing broader domains and connected interests.

### At the outer frontier

Representing concepts currently being explored.

### Newly forming regions

Representing Emerging Threads.

### Faded peripheral material

Representing Dormant Threads.

---

# 11. Example Composition

Suppose the Portrait Model contains:

```text
Dominant domains
Mathematics
Machine Learning
Physics

Anchors
Linear Algebra
Graph Theory

Bridge
Spectral Methods

Emerging
Formal Verification

Frontier
Operator Theory
```

The visual may contain:

```text
Human profile

CORE
• geometric constructions
• matrices
• graph structures

BRIDGE
• Laplacian/eigenvalue imagery
• spectral diagrams

OUTER THREAD
• ML architecture imagery
• physics diagrams

EMERGING REGION
• proof trees
• Lean/type-theory symbolism

FRONTIER
• operator-theoretic notation
```

These are illustrative mappings.

The renderer should derive actual composition from Portrait Model data.

---

# 12. Portrait Model

Create a structured backend object.

Example:

```typescript
interface IntellectualPortrait {
  id: string;
  userId: string;

  generatedAt: string;
  version: number;

  summary: PortraitSummary;

  domains: PortraitDomain[];

  anchors: PortraitNode[];
  bridges: PortraitNode[];
  frontiers: PortraitNode[];

  emergingThreads: PortraitThread[];
  dormantThreads: PortraitThread[];

  connections: PortraitConnection[];

  visualSources: PortraitVisualSource[];

  composition: PortraitComposition;

  evolution: PortraitEvolution;

  confidence: PortraitConfidence;

  algorithmVersion: string;
  configVersion: string;
}
```

---

# 13. Data Inputs

The Portrait Model may use:

```text
user_concepts
concept_edges
mastery
learning_sessions
quiz_attempts
review_history
goals
goal_concepts
pathways
notes
saved_items
search_activity
source_interactions
recent activity
domain clusters
```

Do not count passive ingestion as knowledge.

Example:

Uploading a textbook does NOT mean the user knows its contents.

---

# 14. Activity Strength

Different actions should contribute differently.

Approximate hierarchy:

```text
Concept impression                 very low
Search                             low
Concept opened                     low
Saved                              medium-low
Lesson substantially read          medium
Note created                       medium
Exercise completed                 medium-high
Quiz successfully completed        high
Successful spaced review           high
Repeated successful interaction    very high confidence
Active goal                        strong frontier signal
```

Weights must be configuration-driven.

---

# 15. Mastery vs Activity

Keep these separate.

A concept may be:

```text
high mastery + low recent activity
```

and remain an Anchor.

A concept may be:

```text
low mastery + high recent activity
```

and become a Frontier.

Do not use one generic "importance" number for everything.

---

# 16. Anchor Detection

Anchor score should consider:

$$
A(v)
=
w_mM(v)
+
w_hH(v)
+
w_rR(v)
+
w_cC(v)
$$

where:

* \(M\): mastery
* \(H\): historical interaction strength
* \(R\): repeated successful reinforcement
* \(C\): relevance/connectivity in user's graph

Require meaningful evidence.

A concept should not become an Anchor after one interaction.

---

# 17. Frontier Detection

Frontier score may consider:

$$
F(v)
=
w_gG(v)
+
w_rR(v)
+
w_pP(v)
+
w_nN(v)
-
w_mM(v)
$$

where:

* \(G\): active-goal relevance
* \(R\): recent activity
* \(P\): prerequisite readiness
* \(N\): neighborhood importance
* \(M\): established mastery

Frontiers should represent the boundary of current learning.

---

# 18. Bridge Detection

A Bridge connects significant clusters.

Potential signals:

* betweenness centrality
* cross-cluster edge count
* number of domains connected
* user mastery
* activity
* pathway reuse

Example:

```text
Linear Algebra
├── Machine Learning
├── Quantum Mechanics
└── Spectral Graph Theory
```

Bridge detection must run on the user's graph or relevant user-weighted graph.

Do not merely use global centrality.

---

# 19. Emerging Threads

An Emerging Thread requires multiple pieces of coherent evidence.

Example:

```text
Lean
Dependent Types
Proof Assistants
Formal Verification
Type Theory
```

combined with recent meaningful activity may produce:

```text
Emerging Thread:
Formal Methods
```

Require:

* multiple related concepts
* multiple meaningful interactions
* recent growth

One search must not create an Emerging Thread.

---

# 20. Dormant Threads

A previously significant area may become dormant when recent activity falls substantially.

Never frame this as failure.

Good copy:

> Graph Theory has been quieter recently.

Bad copy:

> You are losing interest in Graph Theory.

The latter is an unjustified psychological claim.

---

# 21. Domain Metrics

Each domain may contain:

```typescript
interface PortraitDomain {
  id: string;
  name: string;

  conceptCount: number;

  mastery: number;
  activity: number;
  interest: number;
  recency: number;
  breadth: number;
  depth: number;

  portraitWeight: number;

  dominantConceptIds: string[];
}
```

Normalize internal scores to:

```text
0.0 → 1.0
```

---

# 22. Breadth and Depth

## Breadth

May use:

* unique concepts
* distinct subtopics
* graph branching
* domain coverage

## Depth

May use:

* prerequisite depth
* advanced concepts
* mastery
* repeated reinforcement
* progression

These influence visual form.

Do not necessarily expose raw scores prominently.

---

# 23. Visual Sources

The portrait should incorporate actual sourced imagery when useful.

Examples:

* historical diagrams
* textbook-style figures
* archival illustrations
* scientific schematics
* maps
* manuscripts
* mathematical constructions
* astronomical plates
* botanical plates
* engineering drawings
* historical technical imagery
* public-domain artwork relevant to subjects

These images should correspond to real interests.

---

# 24. Visual Source Service

Create a dedicated service.

```text
visual_sources/
    discovery
    rights
    ranking
    metadata
    caching
    attribution
```

Conceptual interface:

```python
class VisualSourceProvider:
    async def search(
        self,
        query,
        filters
    ) -> list[VisualAssetCandidate]:
        ...
```

---

# 25. Preferred Visual Repositories

Prioritize repositories with explicit licensing and strong provenance.

Potential sources include:

* Wikimedia Commons
* Europeana
* NASA image repositories where permitted
* national libraries
* museums
* university digital collections
* public-domain archives
* other explicitly licensed cultural/scientific repositories

Do not scrape random Google Image results.

---

# 26. Visual Asset Rights

Every visual asset must have explicit reuse information.

Suggested internal rights classes:

```text
PUBLIC_DOMAIN
CC0
CC_BY
CC_BY_SA
RESTRICTED
UNKNOWN
```

Default automatic composition policy:

### Preferred

```text
PUBLIC_DOMAIN
CC0
```

### Allowed with attribution

```text
CC_BY
```

### Conditional

```text
CC_BY_SA
```

Review implications before automatically creating derivatives.

### Never automatically use

```text
RESTRICTED
UNKNOWN
NC unless explicitly suitable
ND for derivative compositions
```

Do not assume online availability equals permission.

---

# 27. Visual Source Record

```typescript
interface VisualAsset {
  id: string;

  title: string;
  sourceUrl: string;
  canonicalUrl: string;

  creator?: string;
  institution?: string;
  date?: string;

  license: string;
  rightsClass: string;
  attributionText?: string;

  imageUrl: string;
  thumbnailUrl?: string;

  width?: number;
  height?: number;

  concepts: string[];

  relevanceScore: number;
  aestheticScore: number;
  rightsScore: number;
  qualityScore: number;
}
```

---

# 28. Visual Search Query Generation

Portrait concepts may be transformed into visual search queries.

Example:

```text
Concept:
Spectral Graph Theory

Potential queries:
"graph Laplacian historical diagram"
"network eigenvalue mathematical illustration"
"spectral graph theory visualization"
```

LLMs may help generate candidate search queries.

LLMs must NOT fabricate resulting image metadata.

---

# 29. Visual Ranking

Candidate image score:

$$
V(i)
=
w_rR(i)
+
w_aA(i)
+
w_lL(i)
+
w_qQ(i)
+
w_cC(i)
-
w_dD(i)
$$

where:

* \(R\): conceptual relevance
* \(A\): aesthetic compatibility
* \(L\): licensing suitability
* \(Q\): quality/resolution
* \(C\): compositional usefulness
* \(D\): redundancy

Rights suitability should have a hard minimum threshold.

---

# 30. Image Quantity

Do not create giant scrapbook collages.

Initial target:

```text
5–12 meaningful visual assets
```

for a mature portrait.

New users may have:

```text
1–4
```

or even none.

Use negative space intentionally.

---

# 31. Visual Diversity

Avoid selecting ten nearly identical images.

Encourage variation between:

* line diagrams
* photographs
* archival images
* illustrations
* schematics
* manuscripts

where appropriate.

However, visual consistency matters more than arbitrary diversity.

---

# 32. Semantic Provenance

Every sourced visual used in the portrait must know:

```text
what it represents
which concepts selected it
which domain/thread it belongs to
where it came from
what its license is
```

Example:

```json
{
  "visual_asset_id": "...",
  "represents": "Spectral Methods",
  "concept_ids": ["...", "..."],
  "portrait_role": "BRIDGE"
}
```

---

# 33. Interactive Source Inspection

Where practical, hovering/clicking a visual fragment should expose its meaning.

Example:

```text
Spectral Methods

Bridge between:
Graph Theory
Linear Algebra

Visual:
Historical network diagram

Source:
Wikimedia Commons
Public Domain

[ Open thread ]
[ View source ]
[ View in Brain ]
```

The attribution UI should remain subtle.

Do not plaster copyright labels over the portrait.

---

# 34. Portrait Layers

Recommended rendering layers:

```text
1. Background structure
2. Human figure
3. Internal knowledge imagery
4. Domain textures
5. Bridge structures
6. Frontier imagery
7. Emerging accents
8. Graph/constellation overlay
9. Interactive hit regions
10. Labels / UI
```

The exact implementation may vary.

---

# 35. Composition Engine

The canonical portrait must be generated by a deterministic composition engine.

Possible implementation technologies:

* SVG
* Canvas
* WebGL
* PixiJS
* D3
* combination

Before implementing:

* research mature OSS
* inspect licenses
* benchmark likely approach
* record provenance

Do not immediately hand-write a custom rendering system without investigation.

---

# 36. Human Masking

When using a photograph or silhouette, knowledge imagery may be clipped/masked through the human figure.

Possible treatments:

```text
double exposure
layered cutout
masked collage
translucent overlap
contour-bound composition
```

Avoid cheesy automated Photoshop-filter aesthetics.

---

# 37. Portrait Must Remain Data-Legible

The user should be able to understand:

* what major area each region corresponds to
* what is established
* what is emerging
* what is a Bridge
* what lies on the Frontier

The portrait may be artistic but cannot become uninterpretable.

---

# 38. Visual Encoding

Suggested stable mappings:

### Centrality

Intellectual importance.

### Visual density

Depth / maturity.

### Area

Portrait weight.

### Internal placement

Established knowledge.

### Outer placement

Current Frontier.

### Cross-body strand

Bridge.

### Newly illuminated region

Emerging Thread.

### Lower contrast

Dormant Thread.

### Connection lines

Cross-domain relationships.

These mappings should be documented.

---

# 39. Stable Visual Identity

The portrait must not randomly regenerate on refresh.

Use:

```text
stableUserSeed
snapshotId
algorithmVersion
```

to produce deterministic layout.

Major established regions should remain spatially stable between snapshots.

---

# 40. Portrait Evolution

The portrait should visually age with the user.

Example:

```text
Month 1
Sparse silhouette
Three conceptual fragments

Month 6
Dense mathematical core
ML branch growing outward
Formal methods appearing

Month 12
Multiple connected domains
Stable bridges
Several developed frontiers
```

The experience should feel cumulative.

---

# 41. Snapshot History

Persist immutable Portrait Snapshots.

Suggested triggers:

* weekly if meaningful change occurred
* major new Anchor
* major Bridge appears
* new Emerging Thread
* meaningful domain-weight change
* manual refresh after real underlying changes

Do not snapshot every interaction.

---

# 42. Meaningful Change Detection

Do not create a new portrait because:

```text
mastery 74.1 → 74.3
```

Create one because:

```text
Formal Methods became an Emerging Thread
```

or:

```text
Operator Theory became a Frontier
```

or:

```text
Linear Algebra now bridges three active clusters
```

---

# 43. Evolution UI

Profile may eventually show:

```text
YOUR PORTRAIT OVER TIME

March ─── April ─── May ─── June ─── July

                         ▲
                Formal Methods emerged
```

Users can inspect previous portraits.

Historical snapshots must not be recomputed using current data.

---

# 44. Evolution Animation

When moving from one snapshot to another:

* preserve major landmarks
* fade/morph old regions
* grow new strands
* introduce new images gradually
* avoid full random rearrangement

Motion should communicate structural change.

---

# 45. Profile Photograph Handling

If the user uses their own image:

* store securely
* treat as private
* allow replacement
* allow deletion
* allow disabling portrait-photo use without deleting account photo
* avoid unnecessary external processing

If an external image service is ever used, obtain explicit consent.

---

# 46. Discovery Integration

Discovery uses the same Portrait Model but not the same large visual composition.

Example:

```text
YOUR CURRENT SHAPE

Mathematics remains the strongest established region.

Formal Methods is growing quickly.

Linear Algebra remains your strongest bridge.

Operator Theory is your current frontier.

[ portrait thumbnail ]

WHAT CHANGED

+ Formal Verification emerged
+ Functional Analysis deepened
○ Graph Theory became quieter

NEXT CONNECTION

Category Theory may connect...
```

Discovery is analytical and actionable.

---

# 47. Portrait Narrative

Generate at most:

```text
2–4 sentences
```

Example:

> Mathematics remains the most established part of your graph, with linear algebra connecting your machine-learning, physics and graph-theory activity. Formal methods has become a distinct emerging thread, while operator theory currently sits near the boundary of your mastered analysis concepts.

Avoid personality claims.

Forbidden:

> You are an adventurous, interdisciplinary thinker.

Allowed:

> Three currently active domains share linear algebra as their strongest Bridge.

---

# 48. Narrative Pipeline

```text
Lattice DB
    ↓
deterministic scoring
    ↓
Portrait Model
    ↓
structured facts
    ↓
LLM prose rendering
```

The LLM does not decide:

* Anchors
* Bridges
* Frontiers
* Emerging Threads

---

# 49. Explainability

Every classification needs a "Why?"

Example:

```text
Why is Formal Methods emerging?

You interacted meaningfully with
8 related concepts in the last 21 days.

4 were new to your Brain.

2 are connected to an active pathway.
```

Example:

```text
Why is Linear Algebra a Bridge?

It connects 4 significant clusters:
Machine Learning
Graph Theory
Physics
Numerical Methods
```

---

# 50. Portrait Inspector

Clicking a meaningful region opens an inspector.

Example:

```text
LINEAR ALGEBRA

ANCHOR · BRIDGE

Established knowledge
87%

Connects
Machine Learning
Graph Theory
Physics

Why it appears here
Used across four active knowledge clusters.

Visual source
"Geometric interpretation of linear transformations"
...

[ Open concept ]
[ View in Brain ]
[ Explore thread ]
```

---

# 51. Source Attribution UI

Source attribution should be progressively disclosed.

Default portrait:

clean.

Hover/click:

show provenance.

Detailed inspector:

show:

* title
* creator
* institution
* date
* license
* source link

Never display raw metadata noise on the main portrait.

---

# 52. Human Portrait Interaction

The user should interact with knowledge regions, not with arbitrary body parts.

Do not create weird semantics such as:

```text
head = mathematics
heart = literature
hands = engineering
```

unless there is an explicit design rationale.

Avoid pseudoscientific body symbolism.

The human form is a compositional anchor, not a personality diagram.

---

# 53. Portrait Rendering States

## Sparse/new user

Minimal human silhouette.

Few fragments.

Large negative space.

Copy:

> Your portrait is still forming.

## Mature user

Rich but controlled composition.

## Loading

If previous portrait exists:

show it while refreshing.

If first portrait:

show meaningful formation stages.

## Error

Show last valid portrait.

---

# 54. Minimum Evidence

Initial guideline:

### Portrait activation

At least:

```text
10 meaningful concept interactions
```

### Emerging Thread

At least:

```text
3 related concepts
+
3 meaningful recent interactions
```

### Bridge

Must connect:

```text
≥ 2 significant clusters
```

### Anchor

Must satisfy minimum historical evidence and mastery/activity confidence.

Keep configurable.

---

# 55. Confidence

```typescript
interface PortraitConfidence {
  overall: number;

  anchorConfidence: number;
  bridgeConfidence: number;
  frontierConfidence: number;
  emergingThreadConfidence: number;
}
```

Low-confidence portraits should visibly remain sparse and cautiously worded.

---

# 56. Source-Grounded Visual Queries

Visual sourcing should use reputable source metadata just as lesson sourcing does.

Example:

```text
Portrait element:
Quantum Mechanics

Visual source candidates:
• original scientific diagrams
• archival photographs
• historical apparatus
• university/open institutional imagery
```

Do not choose random visually attractive images with weak conceptual relevance.

---

# 57. Factual Source Integration

Portrait insights should connect to Lattice's wider source-grounding architecture.

If the portrait displays a concept explanation, it may reuse:

* lesson sources
* canonical concept sources
* uploaded sources

where appropriate.

The Portrait should not become a parallel factual-generation system.

---

# 58. Optional Generated Artwork

The current optional edition is a source-free deterministic SVG generated from
the portrait composition. A future model-backed raster generator may be added
behind a separate provider and consent flow; it must not replace the
authoritative interactive portrait.

Architecture:

```text
Portrait Model
      │
      ├────────► Canonical interactive portrait
      │
      └────────► Optional generated art edition
```

The generated artwork may use:

* portrait composition
* sourced imagery references
* user-selected visual style

The generated art version is NOT authoritative.

It does not replace the interactive portrait.

---

# 59. Generated Art Safety

Do not feed externally licensed source imagery into a generative image pipeline unless licensing permits that use.

Maintain separate rights decisions for:

```text
display/composition
```

and:

```text
generative derivative use
```

---

# 60. Future Visual Themes

Architecture may support:

```text
Editorial
Constellation
Archive
Topographic
Sigil
Botanical
Orbital
Minimal
```

Do not implement a theme marketplace now.

Initial design should be exceptionally polished before adding variants.

---

# 61. Backend Module

Suggested structure:

```text
portrait/
    service.py
    scoring.py
    clustering.py
    anchors.py
    bridges.py
    frontiers.py
    threads.py
    snapshots.py
    evolution.py
    narrative.py
    composition.py
    models.py
    schemas.py

visual_sources/
    providers/
    discovery.py
    ranking.py
    rights.py
    metadata.py
    cache.py
```

Equivalent clean structure is acceptable.

---

# 62. Portrait Computation Pipeline

```text
Load user graph
       ↓
Aggregate mastery/activity
       ↓
Compute domain metrics
       ↓
Detect clusters
       ↓
Detect Anchors
       ↓
Detect Bridges
       ↓
Detect Frontiers
       ↓
Detect Emerging/Dormant Threads
       ↓
Compare prior snapshot
       ↓
Select visual concepts
       ↓
Search/reuse licensed visual assets
       ↓
Rank assets
       ↓
Generate deterministic composition
       ↓
Generate narrative
       ↓
Persist snapshot
```

---

# 63. Asynchronous Work

Expensive operations should run asynchronously:

* community detection
* visual-source discovery
* image processing
* composition preprocessing
* narrative generation

Profile must not block while rebuilding the entire portrait.

Serve the previous snapshot immediately when available.

---

# 64. Portrait Input Hash

Compute:

```text
portraitInputHash
```

from relevant versioned state.

If unchanged:

```text
POST /portrait/refresh
```

queues the refresh and should leave the current persisted portrait available
until the worker finishes. The worker compares the hash and avoids creating a
new snapshot when the relevant state is unchanged.

---

# 65. API

Suggested endpoints:

```text
GET  /api/portrait
POST /api/portrait/refresh

GET  /api/portrait/history
GET  /api/portrait/{snapshot_id}
GET  /api/portrait/refresh/{job_id}

GET  /api/portrait/{snapshot_id}/element/{element_id}

GET  /api/portrait/{snapshot_id}/visual/{visual_id}

GET  /api/portrait/{snapshot_id}/changes
```

Follow existing project API conventions if different.

---

# 66. Snapshot Storage

Suggested table:

```text
portrait_snapshots

id
user_id

created_at

algorithm_version
config_version
input_hash

portrait_model_json
composition_json
visual_sources_json
change_summary_json

narrative
confidence

is_current
```

JSONB is suitable because the snapshot is immutable.

---

# 67. Visual Asset Storage

Store reusable external assets independently.

```text
visual_assets

id
canonical_url
source_url

title
creator
institution
date

license
rights_class
attribution_text

image_object_key
thumbnail_object_key

width
height
content_hash

retrieved_at
metadata
```

Do not duplicate the same image across snapshots.

---

# 68. Local Caching of Visual Assets

Do not hotlink external imagery in the final portrait where avoidable.

Where licensing and source terms permit:

* fetch
* validate
* store cached copy
* preserve canonical attribution
* preserve source URL

Object storage should serve optimized variants.

Cached portrait image bytes are served through an owner-scoped endpoint. The
browser requests that endpoint with the authenticated session and falls back
to the rights-cleared source URL when the cache is unavailable.

---

# 69. Image Processing

Use mature libraries for:

* resizing
* thumbnails
* masking
* format conversion
* metadata handling

Do not write an image-processing pipeline from scratch.

---

# 70. Rendering Technology Evaluation

Before implementation, compare:

* SVG
* Canvas
* PixiJS/WebGL
* D3-based composition
* CSS masking where appropriate

Requirements:

* interactive regions
* masks
* image layering
* animation
* responsive scaling
* strong performance
* deterministic layout
* export compatibility later

Document decision in:

```text
docs/portrait-rendering.md
```

Decision recorded in `docs/portrait-rendering.md`: SVG is the canonical
semantic portrait renderer; Sigma/WebGL remains isolated to the Brain.

---

# 71. OSS First

Before hand-building anything substantial, inspect mature OSS for:

* portrait/collage layout
* graph clustering
* deterministic layout
* SVG masks
* Canvas/WebGL rendering
* image cropping
* collision detection
* tooltip positioning
* animation
* responsive inspectors

Record reused/adapted code in:

```text
docs/component-provenance.md
```

High quality means using proven foundations when appropriate.

---

# 72. Performance Targets

Cached current portrait API:

```text
< 300ms p95
```

Portrait interactions:

```text
target 60fps
```

Initial visual:

render immediately from persisted composition.

Recomputation:

asynchronous.

External visual source search:

never required on every Profile visit.

---

# 73. Responsive Design

## Desktop

Large portrait + side inspector.

## Tablet

Portrait + drawer inspector.

## Mobile

Simplified composition.

* fewer labels
* touch regions
* bottom-sheet inspector
* preserve major human form

Do not merely scale desktop to 375px.

---

# 74. Accessibility

Provide a textual equivalent.

Example:

```text
INTELLECTUAL PORTRAIT

Dominant domains
1. Mathematics
2. Machine Learning
3. Physics

Anchors
Linear Algebra
Graph Theory

Bridge
Spectral Methods

Frontier
Operator Theory

Emerging
Formal Verification
```

Keyboard navigation must work.

Respect:

```text
prefers-reduced-motion
```

Visual-source descriptions should have meaningful accessibility labels.

---

# 75. Privacy

Portrait data is private by default.

The following remain private:

* intellectual inferences
* mastery
* learning history
* portrait history
* source activity
* uploaded photograph

Future sharing must be opt-in.

---

# 76. User Control

Initial controls:

```text
Use profile photo in portrait
ON/OFF

Refresh portrait

View portrait history
```

Future controls may include:

```text
Hide this thread
This isn't important to me
Make this more prominent
Change portrait style
```

Do not implement advanced controls until core model quality is validated.

---

# 77. Debug Mode

Create developer-only explanation tooling.

For example:

```text
FORMAL METHODS

Emerging Thread score: 0.82

Recent activity:      +0.28
New concepts:         +0.21
Goal relevance:       +0.18
Cluster coherence:    +0.15

Threshold: 0.70
```

Visual source:

```text
Asset relevance:      0.91
Rights suitability:   1.00
Aesthetic score:      0.76
Resolution:           0.88
```

The system must be debuggable.

---

# 78. Golden Fixtures

Create deterministic test users.

## A — New User

Sparse activity.

Expected:

* sparse portrait
* low confidence
* no invented identity

## B — Mathematics Specialist

Expected:

* math-dominant core
* deep internal visual density

## C — Cross-Domain User

Linear algebra used across:

* ML
* physics
* graph theory

Expected:

* Linear Algebra Bridge

## D — Emerging Formal Methods

Recent:

* Lean
* Types
* Logic
* Verification

Expected:

* Formal Methods Emerging Thread

## E — Dormant Domain

Previously strong graph theory, no recent use.

Expected:

* still visible
* lower recent prominence
* not removed

---

# 79. Unit Tests

Test:

* Anchor scoring
* Bridge scoring
* Frontier detection
* Emerging Thread thresholds
* Dormant detection
* confidence
* visual-asset rights filtering
* visual ranking
* deterministic seed
* snapshot immutability
* input hash
* evolution diff

---

# 80. Integration Tests

Example:

```text
new learning activity
      ↓
Portrait Model changes
      ↓
visual-source selection updates
      ↓
new snapshot
      ↓
Profile returns snapshot
      ↓
Discovery returns same underlying classification
```

---

# 81. E2E Tests

Example scenario:

```text
User learns several formal-methods concepts
      ↓
completes quizzes
      ↓
refreshes Portrait
      ↓
Formal Methods appears as Emerging
      ↓
new visual fragment appears
      ↓
clicking it explains why
      ↓
source provenance is accessible
      ↓
Discovery shows same Emerging Thread
```

---

# 82. Visual Regression

Maintain screenshots for:

* no-photo sparse portrait
* photo-based portrait
* mature portrait
* Emerging Thread
* Frontier
* Bridge interaction
* inspector
* mobile
* reduced motion
* old snapshot
* portrait evolution

Use Playwright screenshot tests.

---

# 83. Failure Handling

## Visual-source search fails

Render portrait without that asset.

## One image disappears

Use cached copy if permitted or substitute safely.

## Rights metadata uncertain

Do not use asset.

## Narrative generation fails

Portrait remains functional.

## Portrait computation fails

Return previous snapshot.

## Photo fails

Fall back to non-identifying human silhouette.

## Renderer fails

Show textual portrait.

---

# 84. Analytics

Track:

```text
portrait_viewed
portrait_refreshed

portrait_element_opened
portrait_element_hovered

portrait_visual_source_opened

portrait_brain_navigation
portrait_discovery_navigation

portrait_history_opened
portrait_snapshot_selected

portrait_photo_enabled
portrait_photo_disabled
```

Do not send sensitive underlying text to analytics.

The core implementation records only event type plus portrait, snapshot, and
element identifiers. Photo enable/disable events use the same identifier-only
boundary.

---

# 85. Implementation Phases

The phases below are intentionally split into shippable sub-phases so the
portrait can be validated before the next layer depends on it:

| Phase | Sub-phases |
| --- | --- |
| 1 — Portrait Intelligence | **1a** deterministic inputs and scoring; **1b** classification and confidence; **1c** immutable snapshots, history, and APIs; **1d** golden fixtures, migration smoke, and integration coverage; **1e** developer debug tooling; **1f** configuration-driven thresholds and weights |
| 2 — Human-Centered Renderer | **2a** anonymous human form and accessible text; **2b** deterministic composition and interaction regions; **2c** opt-in photograph mode and responsive/visual regression checks |
| 3 — Visual Source System | **3a** provider and rights gates; **3b** semantic ranking, caching, and deduplication; **3c** attribution and source inspection; **3d** institutional public-domain fallback |
| 4 — Full Profile Portrait | **4a** Profile integration; **4b** Discovery/Brain navigation parity; **4c** narrative, failure handling, and release polish; **4d** privacy-safe interaction analytics; **4e** asynchronous portrait recomputation |
| 5 — Evolution | **5a** snapshot comparison and change detection; **5b** timeline/history UI; **5c** continuity-preserving animation |
| 6 — Advanced Art | **6a** themes; **6b** export/share cards; **6c** optional generated-art editions and safety review |

**Current implementation boundary:** The planned Phase 2c photograph mode,
responsive browser coverage, and Phase 6 presentation editions are now in
place. Profile photographs are private, explicitly opt-in, replaceable,
deletable, and fall back to the anonymous human form on failure. Themes and
source-free SVG share cards are presentation-only; the canonical interactive
portrait remains the authoritative reading.

## Phase 1 — Portrait Intelligence

Build:

* Portrait Model
* scoring
* clustering
* Anchors
* Bridges
* Frontiers
* Emerging Threads
* Dormant Threads
* confidence
* snapshots
* APIs
* debug tooling
* disposable-database migration and integration checks

**1f:** keep portrait thresholds, normalization targets, and scoring weights in
a typed configuration profile, and include that profile in the portrait input
hash so a changed profile creates a new immutable snapshot.

Validate before implementing art.

---

## Phase 2 — Human-Centered Renderer

Build:

* silhouette mode
* optional profile-photo mode
* masks
* layout
* interaction regions
* inspector
* deterministic composition
* responsive behavior

The deterministic layout must anchor each region to its concept, thread, or
asset identifier so sibling insertion/reordering does not move established
regions between snapshots.

The interactive SVG should expose its focusable regions as an accessible
group; the textual portrait index remains the complete equivalent.
Keyboard focus must also have a visible cue on concept and visual-source
regions.

On narrow screens, keep the human form and highest-signal regions while hiding
secondary visual clutter with CSS; the complete textual portrait index remains
available below the composition.

No external imagery required yet.

Use basic internal placeholder fixtures only during development.

---

## Phase 3 — Visual Source System

Build:

* reputable providers
* search
* licensing
* ranking
* caching
* metadata
* attribution
* concept associations

Implementation split:

* **3a–3c:** Wikimedia search, rights gates, shared ranking/cache, durable
  visual refresh work with user/snapshot deduplication, and source inspection;
  academic discovery preserves DOI identity while preferring an HTTPS open-access
  PDF or landing page for ingestion when the provider supplies one.
* **3d:** The Metropolitan Museum of Art Open Access fallback, used only when
  Wikimedia returns fewer than two candidates. Require its public-domain flag,
  title, and HTTPS image URL before shared ranking/cache.

Sourced visual regions should announce the represented concept, source title,
and rights class before the user opens the inspector.

Replace development imagery with real licensed assets.

---

## Phase 4 — Full Profile Portrait

Integrate:

* person
* sourced imagery
* knowledge structures
* interactive regions
* narrative
* source inspection
* Brain navigation
* Discovery navigation
* privacy-safe interaction analytics

Implementation split:

* **4c1:** preserve the last valid portrait and accessible textual index when
  portrait rendering, narrative, or visual-source work fails; use the cached
  image, then the rights-cleared source URL, then a readable unavailable state.
* **4c2:** run visual-source refresh through a durable, user/snapshot-deduped
  job and keep the current portrait visible while pending or failed.
* **4c3:** keep inspector provenance and Brain/Discovery navigation aligned
  across desktop, tablet, and mobile layouts.
* **4c4:** initialize the private profile boundary before portrait events or
  learner feedback write, so first-time authenticated users do not hit a
  profile foreign-key failure.
* **4c5:** keep structured application and Uvicorn records single-emission so
  deployment logs remain readable during background-job failures.
* **4c6:** preserve unhandled request exceptions at the middleware boundary
  while logging their request ID and 500 timing instead of masking them.
* **4c7:** expose the latest source-ingest failure reason in the Library while
  keeping the source record and its retry state intact.
* **4c8:** add browser-level Profile and Discovery contract coverage with
  mocked portrait responses, mobile/reduced-motion checks, and screenshot
  capture.
* **4d:** persist privacy-safe interaction analytics with identifiers only.
* **4e1:** Profile and Discovery expose the refresh control;
  `GET /portrait` and Discovery serve the latest persisted snapshot;
  `POST /portrait/refresh` queues durable `PORTRAIT_REFRESH` work and its
  status endpoint returns the refreshed snapshot when the worker finishes;
  failed recomputation is recorded as failed while reads retain the previous
  snapshot.
* **4e2:** make portrait refresh idempotent per authenticated user while work
  is pending, without preventing a later refresh after a terminal job.

This is the first fully polished release.

---

## Phase 5 — Evolution

Build:

* history
* visual continuity
* snapshot comparison
* timeline
* animated growth

Implementation split:

* **5a:** compare immutable snapshots and record only meaningful structural
  changes in `changes_since_previous`.
* **5b:** expose the history as a keyboard-selectable timeline with a selected
  snapshot detail view.
* **5c1:** animate keyed portrait regions as snapshots change; retain
  identifier-derived positions and category-qualified keys so established
  landmarks do not reshuffle or collide across region types.
* **5c2:** use `prefers-reduced-motion` to disable the enter/exit transition
  while preserving the same snapshot content and interaction order.

---

## Phase 6 — Advanced Art

Implemented presentation layer:

* portrait themes
* export
* share cards
* optional source-free generated-art editions

---

# 86. Definition of Done

The feature is complete when:

1. The Portrait is based on real Lattice data.
2. A human/person element is visibly central.
3. The feature works without a user photograph.
4. User photographs require explicit opt-in.
5. Significant portrait regions encode real concepts or threads.
6. Visual assets are sourced from reputable repositories.
7. Every sourced asset has known provenance.
8. Licensing is validated before use.
9. Unknown/restricted assets are rejected.
10. Visual assets are selected for semantic relevance.
11. The portrait does not look like a random collage.
12. Anchors are explainable.
13. Bridges are explainable.
14. Frontiers are explainable.
15. Emerging Threads require real evidence.
16. Profile and Discovery use the same Portrait Model.
17. The Brain remains distinct from the Portrait.
18. Stable regions remain visually stable over time.
19. Portrait Snapshots are immutable.
20. Evolution is visible and meaningful.
21. Narrative prose does not infer personality.
22. LLMs do not determine Portrait classifications.
23. Failed generation preserves the previous portrait.
24. The experience is responsive.
25. The experience has an accessible textual equivalent.
26. Source attribution is available without cluttering the main artwork.
27. Performance meets targets.
28. Relevant algorithms have automated tests.
29. Main interaction flows have E2E tests.
30. Rendering decisions and OSS provenance are documented.
31. The finished Profile portrait looks intentionally art-directed rather than AI-template-generated.

---

# 87. Final Product Standard

The Intellectual Portrait should combine three things simultaneously:

```text
PERSON
+
KNOWLEDGE
+
TIME
```

The **person** gives the portrait emotional presence.

The **knowledge** makes it truthful.

The **time dimension** makes it alive.

The user should gradually be able to watch their intellectual world accumulate around them.

The Brain is the detailed map.

Discovery explains where the map is changing.

The Portrait turns that map into an image of the person who built it.
