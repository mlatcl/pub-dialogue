---
id: "2026-05-14_cip0011-group-e-evidence-pack-export"
title: "Add export_evidence_pack() and restore export cells to 05_robustness.ipynb"
status: "Completed"
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
- export
- notebooks
---

# Task: Add export_evidence_pack() and restore export cells to 05_robustness.ipynb

## Description

Two evidence-pack export cells from `main-version.ipynb` are absent from the numbered
notebooks:

- `main[93]` — "Export traceability datasets and evidence pack (concerns)": writes an
  HTML paragraph-level evidence pack and an xlsx traceability table linking every concern
  phrase back to its source paragraph and document
- `main[109]` — "Export traceability datasets and evidence pack (benefits)": same for
  benefits

The private helpers `address._clean_for_xlsx()` and `address._yield_row()` already exist.
This task wraps the full export logic into a public
`address.export_evidence_pack(df, cluster_summary_df, kind, output_folder)` function and
adds two notebook cells to `05_robustness.ipynb`.

## Acceptance Criteria

**Library (`pub_dialogue/address.py`):**
- [ ] `address.export_evidence_pack(df, cluster_summary_df, kind, output_folder)` implemented
  - `df`: phrase DataFrame (`concerns_df` or `benefits_df`)
  - `cluster_summary_df`: cluster labels / lens assignments
  - `kind`: `"concern"` | `"benefit"`
  - `output_folder`: `Path` or `str`
  - Writes:
    - `{kind}_evidence_pack.html` — HTML file with one section per cluster, listing
      source paragraphs with document provenance
    - `{kind}_traceability.xlsx` — xlsx with one row per phrase linked to its cluster,
      paragraph, document, and technology
  - Returns a dict `{"html": Path, "xlsx": Path}` of written file paths
  - Unit test: call with small synthetic DataFrames, assert files are written with
    expected columns / structure

**Notebook (`05_robustness.ipynb`):**
- [ ] Two new cells added (one for concerns, one for benefits) calling
      `_address.export_evidence_pack(...)`
- [ ] Cells placed after the existing validation-sample export cell (cell 5)
- [ ] Cells are address-phase only — receive pre-loaded artefacts, no raw data access

## Implementation Notes

The inline code in `main-version.ipynb` cells 93 and 109 uses `html.escape()` for safety
and `openpyxl` (via `pd.ExcelWriter`) for xlsx output — retain both.

The HTML template uses inline CSS for a self-contained file that can be attached to a
paper submission without external dependencies.

`_clean_for_xlsx()` and `_yield_row()` can remain private since they are implementation
details of `export_evidence_pack()`; do not rename them.

## Related

- CIP: 0011
- Source cells: `main-version.ipynb` cell indices 93 and 109
  (code-cell positions 69 and 80)
- `notebook_cell_mapping.json` entries: `main_cell_pos: 69` and `main_cell_pos: 80`

## Progress Updates

### 2026-05-14
Task created (Proposed → Ready). Moderate complexity; logic already exists inline in
main-version.ipynb, so this is primarily a library extraction.
