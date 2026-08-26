# Brain Graph Repair Design

## Goal

Give every concept a stable semantic domain, regenerate only AI-owned graph edges, and keep user-created relationships untouched.

## Root cause

Pathway generation accepts arbitrary prerequisite names but emits no domain. `persist_pathway()` therefore writes generated concepts with `domain = NULL`; the live graph has 110 equal-weight AI prerequisite edges and only two user relationships. Louvain is consequently clustering connectivity, not subject matter.

## Design

- Generated concepts include a required, normalized broad domain (for example, `Formal Verification` or `Criminal Psychology`). The pathway prompt requires the same exact domain label for concepts in the same subject area.
- Validation rejects blank domains, normalizes whitespace, and rejects prerequisites that do not point from an earlier section to a later section. This retains the existing DAG check but removes arbitrary same-pathway links.
- An admin-only Windows-venv script performs an audit first: it writes a JSON report of all proposed domain assignments and AI edge changes, then requires `--apply` to mutate data. It never changes `created_by = 'user'` edges.
- The script groups existing concepts by pathway, asks the configured structured LLM to classify domains and propose only supported `PREREQUISITE` and `RELATED_TO` relations, validates them with the same rules, then replaces only `ai:pathway_generation:*` and `ai:domain_bridge:*` rows. Each new edge records its generator and confidence.
- The Brain API exposes edge confidence/provenance so the client can use only prerequisite/part-of structure for islands and render related links as cross-island context.

## Safety

The first execution is dry-run only. Applying requires an explicit flag after reviewing the generated report. Existing user edges remain unchanged.
