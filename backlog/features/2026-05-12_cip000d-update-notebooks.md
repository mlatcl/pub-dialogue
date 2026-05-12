---
id: "2026-05-12_cip000d-update-notebooks"
title: "Update notebooks to use pub_dialogue.access/assess/address module imports"
status: "Completed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: [
  "2026-05-12_cip000d-update-utils-py",
  "2026-05-12_cip000d-update-init-py"
]
tags:
- backlog
- cip000d
- access-assess-address
- notebooks
---

# Task: Update notebooks to use pub_dialogue.access/assess/address module imports

## Description

Replace all inline function definitions in notebooks with calls to the
corresponding `pub_dialogue` module functions. Five notebooks require changes.

### `00_data_quality.ipynb`

- **Cell 4** (ASSESS plot): replace inline matplotlib figure code with
  `pub_dialogue.assess.plot_data_quality(chunks_df, OUTPUT_FOLDER)`
- **Cell 5** (ASSESS flags): replace `_looks_like_bibliography` +
  `_looks_like_table_row` definitions + flag computation with
  `pub_dialogue.assess.flag_chunk_quality(chunks_df, OUTPUT_FOLDER)`

### `01_processing.ipynb`

- **Cell 7** (imports): add `from pub_dialogue import assess, address` or
  equivalent named imports
- **Cell 13** (ASSESS): replace with `assess.plot_data_quality(chunks_df, OUTPUT_FOLDER)`
- **Cell 14** (ASSESS): replace with `assess.flag_chunk_quality(chunks_df, OUTPUT_FOLDER)`
- **Cell 16** (ADDRESS): replace inline `_record_failure`,
  `_phrase_contains_tech_term`, `extract_concerns_from_paragraph` definitions
  with import + call
- **Cell 22** (ADDRESS): same for benefit counterparts
- **Cells 20, 25** (ADDRESS): remove duplicate `get_embeddings_batch`
  definitions, use already-imported function from `pub_dialogue.address`

### `01a_clustering.ipynb`

- **Cell 6** (imports): add `label_cluster`, `label_benefit_cluster`,
  `run_for_k` from `pub_dialogue.address`
- **Cell 8**: replace inline `_load_json` helper with inline one-liner
  (`json.loads(Path(...).read_text())`) or import from utils
- **Cell 14** (ADDRESS): call already-imported `label_cluster` (no change
  to call site)
- **Cell 25** (ADDRESS): remove `label_benefit_cluster` definition, use import
- **Cells 29–30** (ADDRESS): replace `run_for_k` definitions with
  `address.run_for_k(kind="concern", ...)` and
  `address.run_for_k(kind="benefit", ...)`

### `04_temporal_dynamics.ipynb`

- **Cell 2** (ADDRESS): remove `assign_window` definition, use
  `from pub_dialogue.address import assign_window`
- **Cell 10** (ADDRESS): remove `_parse_listcol`, `_assign_window`,
  `_peak_window` definitions, use imports

### `05_robustness.ipynb`

- **Cell 2** (ADDRESS): remove `_clean_for_xlsx` definition, use
  `from pub_dialogue.address import _clean_for_xlsx`

### No changes needed

- `02_shared_structure.ipynb` — no standalone inline defs to migrate
- `03_ai_distinctiveness.ipynb` — nested one-liner helpers (`pretty_cluster`,
  `label`) are too notebook-local to extract

## Acceptance Criteria

- [ ] `00_data_quality.ipynb` cells 4–5 use module functions, no inline defs
- [ ] `01_processing.ipynb` cells 13–14 use `assess.*`, cells 16/22 use `address.*`, no duplicate `get_embeddings_batch`
- [ ] `01a_clustering.ipynb` cell 25 uses imported `label_benefit_cluster`, cells 29–30 use `run_for_k(kind=...)`
- [ ] `04_temporal_dynamics.ipynb` cells 2/10 use imported functions
- [ ] `05_robustness.ipynb` cell 2 uses imported `_clean_for_xlsx`
- [ ] All notebooks execute top-to-bottom without errors (manual smoke test)

## Implementation Notes

Notebook cells should be made as short as possible — ideally a single import
line followed by the function call. Any configuration (prompt text, thresholds)
that previously lived inline should either pass as arguments or use defaults
defined in the module.

## Related

- CIP: 000D

## Progress Updates

### 2026-05-12

Task created.
