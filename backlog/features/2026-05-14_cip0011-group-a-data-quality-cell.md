---
id: "2026-05-14_cip0011-group-a-data-quality-cell"
title: "Restore data-quality summary chart to 00_data_quality.ipynb"
status: "Ready"
priority: "Low"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0011"]
owner: ""
dependencies: []
tags:
- backlog
- notebooks
- assess
---

# Task: Restore data-quality summary chart to 00_data_quality.ipynb

## Description

`main-version.ipynb` cell `main[11]` ("Summarise paragraph-level data quality") produces a
2×2 matplotlib figure showing chunk counts by technology, by year, by length distribution,
and by content-quality flag. It is absent from `00_data_quality.ipynb`.

`assess.plot_data_quality()` (introduced in CIP-000C / CIP-000D) already encapsulates this
logic. The fix is a single notebook cell.

## Acceptance Criteria

- [ ] `00_data_quality.ipynb` contains a cell that calls `assess.plot_data_quality(chunks_df)`
      (or equivalent assess-phase API) and displays the 2×2 chart
- [ ] The cell is positioned after the existing chunk-quality diagnostic cell
- [ ] Running the cell does not raise an error on the standard checkpoint set
- [ ] No access- or address-phase calls are made from this cell

## Implementation Notes

This is purely a notebook change — no library edits required.

```python
# Assess phase: data quality summary
from pub_dialogue import assess as _assess
_assess.plot_data_quality(chunks_df)
```

Check the exact signature of `assess.plot_data_quality` before adding the cell.

## Related

- CIP: 0011
- Source cell: `main-version.ipynb` cell index 11 (code-cell position 7)
- `notebook_cell_mapping.json` entry: `main_cell_pos: 7`

## Progress Updates

### 2026-05-14
Task created (Proposed → Ready). No library changes needed; notebook-only fix.
