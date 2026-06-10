---
id: "2026-06-10_cip0013-add-section-10d-robustness"
title: "Add SECTION 10D lens-scheme sensitivity to 05_robustness.ipynb"
status: "Completed"
priority: "High"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: ["2026-06-10_cip0013-generate-lens-grouping-method"]
tags:
- backlog
- framing-lenses
- sensitivity
- robustness
- cip0013
---

# Task: Add SECTION 10D lens-scheme sensitivity to 05_robustness.ipynb

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Insert a new **SECTION 10D: M6(e) Lens-scheme sensitivity** into
`05_robustness.ipynb` after the existing Section 10C (prompt sensitivity, the
last cell before the export section). The section consists of:

1. A markdown cell with a section header and design description
2. A code cell that runs the LLM lens-grouping step N=5 times on the same fixed
   cluster labels and reports how consistently AI over-indexes on the most
   privacy/data-salient lens

The code cell calls `_address.generate_lens_grouping()` (added in the companion
task) so it always exercises the LLM regardless of cached or canonical files.

## Acceptance Criteria

- [ ] Markdown cell is present with section heading "SECTION 10D: M6(e) Lens-scheme sensitivity"
- [ ] Code cell runs to completion producing:
  - `outputs/lens_sensitivity_summary.csv` (one row per run, N=5)
  - `outputs/lens_sensitivity_all_runs.csv` (one row per lens per run)
- [ ] The print output includes a direction-consistency count ("consistent in X/5 runs")
      and the pp range for the most-AI-salient lens
- [ ] The markdown result line is filled in after running

## Implementation Notes

Insert after cell 39 (last Section 10C cell) and before cell 40 (export cell).
The code structure is specified in CIP-0013 Part B.

Key variables expected to already be in scope from cell 1's `load_artifacts()`:
- `concerns_df` (with `cluster_id` and `technology_meta` columns)
- `cluster_labels` / `cluster_labels_dict`
- `cluster_exemplars`
- `_address` (AddressStage instance)
- `client` (LLMClient)
- `OUTPUT_FOLDER`

Check cell 1 of the robustness notebook to confirm these are available; add any
missing loads before the Section 10D code cell.

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.

Implemented: two cells added to 05_robustness.ipynb after cell 39 (last
Section 10C cell). Markdown cell provides design description and result
placeholder; code cell calls _address.generate_lens_grouping() N=5 times,
computes AI share per lens per run, finds the most-AI-salient lens each run,
and reports direction-consistency count and pp range.
