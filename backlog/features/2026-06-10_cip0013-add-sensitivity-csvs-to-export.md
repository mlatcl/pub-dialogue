---
id: "2026-06-10_cip0013-add-sensitivity-csvs-to-export"
title: "Add lens sensitivity CSVs to export cell in 05_robustness.ipynb"
status: "Completed"
priority: "Low"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: ["2026-06-10_cip0013-add-section-10d-robustness"]
tags:
- backlog
- exports
- sensitivity
- cip0013
---

# Task: Add lens sensitivity CSVs to export cell

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add `lens_sensitivity_summary.csv` and `lens_sensitivity_all_runs.csv` to the
manifest / export cell (cell 40) in `05_robustness.ipynb` so they are included
in the outputs zip when the notebook is packaged for sharing.

## Acceptance Criteria

- [ ] Export cell includes both new CSVs in its file list / zip manifest
- [ ] Running the export cell after Section 10D produces an outputs zip that
      includes both files

## Implementation Notes

Locate the export/manifest cell (currently cell 40) and add the two filenames
to the list of expected outputs. The exact format depends on how the manifest
is structured in that cell — follow the same pattern as existing entries.

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.

No code change required. The export cell (05_robustness.ipynb) uses
`OUTPUT_DIR.rglob("*")` which automatically includes all files in outputs/,
so `lens_sensitivity_summary.csv` and `lens_sensitivity_all_runs.csv` will
be zipped as soon as they exist.
