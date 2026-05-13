---
id: "2026-05-13_cip0010-phase3-pipeline-methods"
title: "CIP-0010 Phase 3: Add AddressStage pipeline methods (cluster, label, lenses)"
status: "Ready"
priority: "Low"
created: "2026-05-13"
last_updated: "2026-05-13"
owner: ""
dependencies:
  - "2026-05-13_cip0010-phase2-computation-methods"
related_cips: ["0010"]
tags:
- backlog
- refactor
- oo-design
- stage-classes
---

# Task: CIP-0010 Phase 3 — AddressStage pipeline methods

## Description

Wrap the heavier pipeline steps from `01a_clustering.ipynb` into `AddressStage` methods,
thinning out the clustering notebook cells.

## Acceptance Criteria

- [ ] `AddressStage.cluster(concerns_df, benefits_df, embeddings)` — runs k-means, returns
  updated DataFrames + centroids dict
- [ ] `AddressStage.label_clusters(client, centroids, concerns_df)` — returns `cluster_labels` dict
- [ ] `AddressStage.assign_framing_lenses(client, cluster_labels, concerns_df)` — returns
  `framing_lens_mappings`
- [ ] `01a_clustering.ipynb` cells replaced with method calls
- [ ] Unit tests added with mocked `LLMClient`
- [ ] `pytest tests/ -v` fully green
- [ ] `01a_clustering.ipynb` executes clean via `nbconvert`

## Related

- CIP: 0010
- Depends on: Phase 2

## Progress Updates

### 2026-05-13
Task created. Depends on Phase 2.
