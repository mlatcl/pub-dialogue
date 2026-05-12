---
id: "2026-05-12_cip000d-create-assess-py"
title: "Create pub_dialogue/assess.py — data assessment module"
status: "Completed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: ["2026-05-12_cip000d-create-access-py"]
tags:
- backlog
- cip000d
- access-assess-address
- assess
---

# Task: Create pub_dialogue/assess.py — data assessment module

## Description

Create `pub_dialogue/assess.py` as the second pipeline-stage module
implementing CIP-000D. This module encapsulates the **assess** stage:
question-agnostic, reusable data characterisation. It must be fully importable
without an API key or LLM client.

**Migrate from `pub_dialogue/utils.py`:**

- **Constants**: `META_VOCABULARY`, `PRIVACY_TERMS`, `_PRIVACY_PATTERN`
- `validate_extraction_cache()`
- `write_extraction_diagnostics()`
- `filter_missing_source_text()`
- `is_privacy_text()`
- `entropy_by_year()`
- `vocabulary_frequency_diagnostic()`
- `generate_validation_summary()`

**Migrate from notebooks (currently duplicated inline):**

- `_looks_like_bibliography()` — defined in `00_data_quality.ipynb` cell 5
  and `01_processing.ipynb` cell 14
- `_looks_like_table_row()` — same duplication

**New wrapper functions (encapsulate notebook cell logic):**

- `plot_data_quality(chunks_df, output_folder)` — wraps the 2×2 matplotlib
  figure logic currently in `00_data_quality.ipynb` cell 4 /
  `01_processing.ipynb` cell 13; saves `data_quality_overview.png`
- `flag_chunk_quality(chunks_df, output_folder)` — wraps quality-flag
  computation + CSV export currently in cell 5 / cell 14; saves
  `chunk_quality_flagged.csv`

Add `__all__` listing all public names.

## Acceptance Criteria

- [ ] `pub_dialogue/assess.py` exists and is importable
- [ ] `import pub_dialogue.assess` succeeds with no API key set
- [ ] All listed functions are present with original signatures intact
- [ ] `_looks_like_bibliography` and `_looks_like_table_row` present with same logic
- [ ] `plot_data_quality(chunks_df, output_folder)` produces `data_quality_overview.png`
- [ ] `flag_chunk_quality(chunks_df, output_folder)` produces `chunk_quality_flagged.csv`
- [ ] `__all__` defined

## Implementation Notes

The key invariant for this module: no function body should import `openai`,
`litellm`, or any LLM-related package at any level of the call stack. If a
function needs an LLM, it belongs in `address.py`.

`plot_data_quality` and `flag_chunk_quality` are new public functions — extract
and consolidate the repeated notebook cell logic into them. The notebook cells
will be replaced with single calls to these functions.

## Related

- CIP: 000D
- Requirement: REQ-0006
- Tenet: access-assess-address

## Progress Updates

### 2026-05-12

Task created.
