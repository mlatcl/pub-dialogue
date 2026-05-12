---
id: "2026-05-12_cip000d-create-address-py"
title: "Create pub_dialogue/address.py — research question addressing module"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: ["2026-05-12_cip000d-create-access-py", "2026-05-12_cip000d-create-assess-py"]
tags:
- backlog
- cip000d
- access-assess-address
- address
---

# Task: Create pub_dialogue/address.py — research question addressing module

## Description

Create `pub_dialogue/address.py` as the third pipeline-stage module
implementing CIP-000D. This module encapsulates the **address** stage:
LLM extraction, embedding, clustering, and analysis functions that are
specific to the research question.

**Migrate from `pub_dialogue/utils.py`:**

- **Constants**: `EXTRACTION_PROMPT`, `BENEFIT_EXTRACTION_PROMPT`, `_SENTINELS`
- `ExtractionResult` dataclass
- `extract_phrases()`
- `get_embeddings_batch()`
- `label_cluster()`
- `ai_fingerprint_over_crosscut()`
- `run_sensitivity()` (lazy-imports `sklearn`, `matplotlib`)
- `_volume_table()`
- `_top_clusters()`

**Migrate from notebooks (inline → address.py):**

- From `01_processing.ipynb` cell 16: `_record_failure()`,
  `_phrase_contains_tech_term()`, `extract_concerns_from_paragraph()`
- From `01_processing.ipynb` cell 22: `_record_benefit_failure()`,
  `_benefit_phrase_contains_tech_term()`, `extract_benefits_from_paragraph()`
- From `01a_clustering.ipynb` cell 25: `label_benefit_cluster()`
- From `01a_clustering.ipynb` cells 29–30: two `run_for_k()` definitions
  (concerns and benefits) — unify into `run_for_k(kind, ...)` where
  `kind` ∈ `{"concern", "benefit"}`
- From `04_temporal_dynamics.ipynb` cell 2: `assign_window()`
- From `04_temporal_dynamics.ipynb` cell 10: `_parse_listcol()`,
  `_assign_window()`, `_peak_window()`
- From `05_robustness.ipynb` cell 2: `_clean_for_xlsx()`

Add `__all__` listing all public names.

## Acceptance Criteria

- [ ] `pub_dialogue/address.py` exists and is importable
- [ ] All listed functions present with original signatures
- [ ] `ExtractionResult` importable from `pub_dialogue.address`
- [ ] `extract_concerns_from_paragraph` and `extract_benefits_from_paragraph`
  present (migrated from notebook inline definitions)
- [ ] `label_benefit_cluster` present
- [ ] Unified `run_for_k(kind, ...)` present, accepting `kind="concern"` or
  `kind="benefit"`
- [ ] `assign_window`, `_parse_listcol`, `_assign_window`, `_peak_window`,
  `_clean_for_xlsx` present
- [ ] `__all__` defined for public names

## Implementation Notes

`run_for_k` currently exists as two near-identical functions (one for concerns,
one for benefits) in `01a_clustering.ipynb` cells 29–30. Unify them with a
`kind` parameter; the notebook calls become `run_for_k(kind="concern", ...)` and
`run_for_k(kind="benefit", ...)`.

The `_phrase_contains_tech_term` and `_benefit_phrase_contains_tech_term`
functions in the notebook are nearly identical — consider unifying into one
`_phrase_contains_tech_term(phrase, tech_words)` function.

## Related

- CIP: 000D
- Requirement: REQ-0006

## Progress Updates

### 2026-05-12

Task created.
