---
id: "2026-05-14_cip0011-group-c-volume-top-clusters"
title: "Make volume_table / top_clusters public and restore output cells to 02_shared_structure.ipynb"
status: "Ready"
priority: "Medium"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0011"]
owner: ""
dependencies: []
tags:
- backlog
- address
- notebooks
---

# Task: Make volume_table / top_clusters public and restore output cells to 02_shared_structure.ipynb

## Description

Two summary tables from `main-version.ipynb` are missing from the numbered notebooks:

- `main[87]` — "Compare volume (phrase counts and paragraph incidence)": a side-by-side
  table of concern vs benefit counts and paragraph incidence rates by technology and year
- `main[88]` — "Top clusters side-by-side (overall)": the top-10 concern and benefit
  clusters by phrase count, shown in a single combined table

Both helper functions already exist in `pub_dialogue/address.py` as private methods
(`_volume_table` and `_top_clusters`). `02_shared_structure.ipynb` contains comment stubs
noting these are "imported from dialogue_utils" but has no working output cells.

This task makes both functions public and adds the missing notebook cells.

## Acceptance Criteria

- [ ] `address._volume_table` renamed to `address.volume_table` (underscore removed)
- [ ] `address._top_clusters` renamed to `address.top_clusters` (underscore removed)
- [ ] All internal callers in `address.py` updated to use the new names
- [ ] Existing unit tests updated for renamed functions (no logic change)
- [ ] `02_shared_structure.ipynb` contains a working cell for the volume comparison table,
      calling `_address.volume_table(concerns_df, benefits_df)` and displaying output
- [ ] `02_shared_structure.ipynb` contains a working cell for the top-clusters side-by-side
      table, calling `_address.top_clusters(...)` for both concern and benefit and
      displaying the combined table
- [ ] Stub comment cells replaced (not duplicated)
- [ ] No raw data access or assess-phase calls in the new notebook cells

## Implementation Notes

The rename is the only library change — no logic changes expected. Verify with `rg "_volume_table\|_top_clusters"` before and after to catch all call sites.

In the notebook the two calls follow this pattern:
```python
vol = _address.volume_table(concerns_df, benefits_df)
display(vol.style.format("{:.1%}", subset=pd.IndexSlice[:, vol.filter(like='incidence').columns]))

top = pd.concat([
    _address.top_clusters(concerns_df, concern_summary_df, "concern"),
    _address.top_clusters(benefits_df, benefit_summary_df, "benefit"),
])
display(top)
```

## Related

- CIP: 0011
- Source cells: `main-version.ipynb` cell indices 87 and 88 (code-cell positions 67 and 68)
- `notebook_cell_mapping.json` entries: `main_cell_pos: 67` and `main_cell_pos: 68`

## Progress Updates

### 2026-05-14
Task created (Proposed → Ready). Rename-only library change; low risk.
