---
id: "2026-05-14_cip0011-group-b-cross-tech-heatmap"
title: "Add cross_technology_heatmap() and restore heatmap cells to 02_shared_structure.ipynb"
status: "Ready"
priority: "High"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0011"]
owner: ""
dependencies: []
tags:
- backlog
- address
- visualisation
- notebooks
---

# Task: Add cross_technology_heatmap() and restore heatmap cells to 02_shared_structure.ipynb

## Description

Two heatmap visualisations from `main-version.ipynb` are missing from the numbered notebooks:

- `main[40]` — "Visualise cross-technology concern distribution" (heatmap of top-40 concern
  clusters × all technologies, coloured by document-weighted salience)
- `main[77]` — "Visualise cross-technology benefit distribution" (same for benefits)

No library function yet exists for this visualisation. This task adds
`address.cross_technology_heatmap(salience_df, cluster_labels, kind, top_n=40)` to
`pub_dialogue/address.py` and then adds two notebook cells to `02_shared_structure.ipynb`.

## Acceptance Criteria

- [ ] `address.cross_technology_heatmap(salience_df, cluster_labels, kind, top_n=40)` is
      implemented in `pub_dialogue/address.py`
      - `salience_df`: DataFrame indexed by document/technology with cluster-id columns
        (output of `address.concern_salience()` or `address.benefit_salience()`)
      - `cluster_labels`: dict mapping cluster id → label string
      - `kind`: `"concern"` or `"benefit"` (used for axis labels)
      - `top_n`: number of clusters to show (default 40)
      - Returns a `plotly` Figure (consistent with other project visualisations)
- [ ] Unit test in `tests/test_address.py` covering the new function with a synthetic
      3-technology × 10-cluster salience matrix
- [ ] `02_shared_structure.ipynb` contains two new cells (one concern, one benefit) placed
      after the dendrogram cells and before the embedding-space visualisation cells
- [ ] Cells use the address-phase call pattern:
      `fig = _address.cross_technology_heatmap(concern_salience_df, CLUSTER_LABELS, "concern")`
- [ ] No raw data access or assess-phase calls in the new notebook cells

## Implementation Notes

The heatmap in `main-version.ipynb` uses `plotly.graph_objects.Heatmap` with:
- x-axis: technology names (sorted by document count descending)
- y-axis: top-N cluster labels (sorted by mean salience descending)
- z-values: document-weighted salience per technology per cluster

Key decisions to preserve from `main-version`:
- Normalise each technology column independently (so rare technologies are not washed out)
- Use `pretty_label()` for cluster labels (truncate long labels)
- Show only clusters that appear in at least one technology above a threshold

The function should not assume a specific colorscale — use `"Blues"` as a sensible default
with a `colorscale` parameter for overrides.

## Related

- CIP: 0011
- Source cells: `main-version.ipynb` cell indices 40 and 77 (code-cell positions 31 and 60)
- `notebook_cell_mapping.json` entries: `main_cell_pos: 31` and `main_cell_pos: 60`

## Progress Updates

### 2026-05-14
Task created (Proposed → Ready). Requires new library function before notebook cells can be added.
