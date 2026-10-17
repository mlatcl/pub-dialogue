---
id: "2026-10-17_adopt-member-mean-centroids-and-sigma2-harden"
title: "Adopt multilogue member-mean centroids + hardened σ²* selection"
status: "Proposed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "bugs"
related_cips: []
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- multilogue
- soft
- centroids
- sigma2
- consumer
---

# Task: Adopt multilogue member-mean centroids + hardened σ²* selection

## Description

Pub-dialogue still builds topic-space centroids from sklearn `KMeans.cluster_centers_` (`address.py`, multiverse k-means sites). Multilogue is gaining a single centroid definition (normalised member means) and a hardened σ²\* rule for flat between-run EMD. Once those land, pub should consume them so study runs and multiverse grids do not silently disagree with formats / multilogue on soft membership.

Triggered by formats replay investigation: fresh sklearn centres vs freeze-path member means flipped soft-lens σ²\* under degenerate EMD; the same sklearn-vs-mean gap exists in pub’s clustering call sites.

## Acceptance Criteria

- [ ] Clustering / multiverse paths that feed soft PPCA use the same centroid definition as multilogue (member means after labels are fixed) — via `multilogue.cluster` or a thin local helper that matches it
- [ ] σ²\* / constrained selection goes through multilogue after the harden lands (no divergent local band/tie-break)
- [ ] Existing soft / multiverse σ² tests updated or extended for the documented degenerate case
- [ ] Short note in progress or CIP compression: whether any published sensitivity tables need re-check under the new tie-break

## Implementation Notes

- Depends on multilogue backlog:
  - `2026-10-17_unify-member-mean-centroids`
  - `2026-10-17_harden-sigma2-flat-emd-selection`
- Keep status **Proposed** until those multilogue tasks are Ready→Completed; then move this to Ready and implement on the multilogue-depend branch (e.g. `cip0005-depend-multilogue` or successor).
- Do not re-implement PPCA math locally — thin onto `multilogue.soft` / `multilogue.cluster`.

## Related

- Multilogue tasks: `2026-10-17_unify-member-mean-centroids`, `2026-10-17_harden-sigma2-flat-emd-selection`
- Multilogue CIPs: 0001 (cluster), 0005 (soft), 0006 (σ² rules)
- Related pub backlog: `2026-10-16_cip0005-finish-pub-soft-distance-adopt` (in multilogue repo consumer list), thin-pub tasks
- Precedent: `ai-dialogue-formats` PR #7 (member-mean unify)

## Progress Updates

### 2026-10-17

Task created (Proposed). Waiting on multilogue library fixes before consumer adoption.

Later same day: design discussion opened [CIP-0017](../../cip/cip0017.md) / [REQ-000A](../../requirements/req000A_soft-throughout-topic-geometry.md) (soft-throughout MPPCA topics). This bug remains the **interim** harden for the hard-k-means + soft-lens stack; CIP-0017 is the intended end state and supersedes deepening local centroid helpers once Accepted.
