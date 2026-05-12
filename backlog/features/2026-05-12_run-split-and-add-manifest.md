---
id: "2026-05-12_run-split-and-add-manifest"
title: "Run split script and add manifest cell to 01_processing.ipynb"
status: "In Progress"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000A"]
owner: ""
dependencies: ["2026-05-12_write-split-script", "2026-05-12_add-load-artifacts"]
tags:
- backlog
- notebook-split
---

# Task: Run split script and add manifest cell to 01_processing.ipynb

## Description

Run `scripts/split_notebook.py` to produce the 6 thematic notebooks, then add
a manifest cell to `01_processing.ipynb` that asserts and reports every expected
artifact file with its shape/row count. This is the final step of the split.

## Acceptance Criteria

- [ ] All 6 notebooks exist in repo root after script run
- [ ] `01_processing.ipynb` manifest cell asserts 15+ expected artifacts
- [ ] Full pytest suite passes after all changes

## Implementation Notes

Manifest cell asserts existence of:
- `paragraph_chunks.csv`, `paragraph_chunks_per_document.csv`
- `extracted_concerns.csv`, `extracted_benefits.csv`
- `cluster_labels.json`, `cluster_summary.csv`
- `benefit_cluster_labels.json`, `benefit_cluster_summary.csv`
- `framing_lens_mappings.json`, `benefit_framing_lens_mappings.json`
- `cluster_entropy.json`, `benefit_cluster_entropy.json`
- `cluster_exemplars.json`, `benefit_cluster_exemplars.json`
- Checkpoint: `concern_embeddings.npy`, `benefit_embeddings.npy`
- Checkpoint: `cluster_centroids.npy`, `benefit_cluster_centroids.npy`

## Related

- CIP: 000A

## Progress Updates

### 2026-05-12

Task created. In Progress — implementing as part of CIP-000A notebook split.
