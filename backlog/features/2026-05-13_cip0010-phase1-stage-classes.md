---
id: "2026-05-13_cip0010-phase1-stage-classes"
title: "CIP-0010 Phase 1: Add AccessStage, AssessStage, AddressStage config classes"
status: "Completed"
priority: "Medium"
created: "2026-05-13"
last_updated: "2026-05-13"
owner: ""
dependencies: []
related_cips: ["0010"]
tags:
- backlog
- refactor
- oo-design
- stage-classes
---

# Task: CIP-0010 Phase 1 — Stage classes and config centralisation

## Description

Add three `@dataclass` config classes — `AccessStage`, `AssessStage`, `AddressStage` — to
their respective modules. In this phase they hold **configuration only** (typed fields with
defaults matching existing hardcoded constants). No new computation methods yet.

Update all five analysis notebook setup cells to instantiate the stage objects and read
constants from them, replacing the repeated inline constant definitions.

## Acceptance Criteria

- [x] `AccessStage` added to `pub_dialogue/access.py` with fields: `output_folder`,
  `checkpoint_folder`, `pdf_folder`, `min_chunk_words`, `max_chunk_words`, `min_chunk_chars`
- [x] `AssessStage` added to `pub_dialogue/assess.py` with field `access: AccessStage`
- [x] `AddressStage` added to `pub_dialogue/address.py` with fields: `access`, `n_concern_clusters`,
  `n_benefit_clusters`, `random_seed`, `tech_col`, `ai_tech_label`,
  `cross_cutting_threshold`, `soft_membership_threshold`, `validation_sample_n`
- [x] All three re-exported from `pub_dialogue/utils.py` and `pub_dialogue/__init__.py`
- [x] Notebook setup cells in `02`, `03`, `04`, `05` instantiate `AccessStage` and
  `AddressStage` and read constants from them
- [x] `TestAccessStageDefaults`, `TestAddressStageDefaults`, `TestAssessStageDefaults` test classes added (19 tests); all defaults match hardcoded notebook values
- [x] `pytest tests/ -v` fully green (293 passed)
- [x] Smoke test: `AccessStage().load_artifacts()` returns correct artifacts from disk

## Implementation Notes

Defaults for each field should match current hardcoded values:
- `n_concern_clusters = 75`, `n_benefit_clusters = 75`
- `random_seed = 42`
- `tech_col = "technology_meta"`, `ai_tech_label = "AI"`
- `cross_cutting_threshold = CROSSCUTTING_ENTROPY_THRESHOLD` (0.5)
- `soft_membership_threshold = 0.3`
- `validation_sample_n = 250`
- `output_folder = Path("outputs")`, `checkpoint_folder = Path("checkpoints")`

All existing module-level functions are kept unchanged — the dataclass is additive.

## Related

- CIP: 0010
- Follows: CIP-000D (module structure), CIP-000F (notebook imports)

## Progress Updates

### 2026-05-13
Task created. CIP-0010 accepted. Ready to implement.

### 2026-05-13 (implementation)
Completed Phase 1. Added `AccessStage`, `AssessStage`, `AddressStage` dataclasses to their
respective modules. All three re-exported from `utils.py` and `__init__.py`. Setup cells updated in
notebooks 02–05. 19 new TDD tests written and passing. Full suite: 293 passed.
