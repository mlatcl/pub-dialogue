---
id: "2026-05-13_fynesse-compliance-fixes"
title: "Fix Fynesse AAA compliance: module misplacements and notebook API setup"
status: "Completed"
priority: "High"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000A"]
owner: ""
dependencies: []
tags:
- backlog
- fynesse
- notebook-split
- architecture
---

# Task: Fix Fynesse AAA compliance: module misplacements and notebook API setup

## Description

Review of the CIP-000A notebook split against the Fynesse Access → Assess →
Address framework identified several genuine violations that needed fixing
before the remaining split work proceeded:

1. **Module misplacements in `assess.py`**: four functions that depend on
   extraction outputs (address-stage artefacts) were incorrectly placed in
   the assess module:
   - `validate_extraction_cache` — validates LLM extraction cache
   - `write_extraction_diagnostics` — yield diagnostics post-extraction
   - `entropy_by_year` — cluster entropy; clusters are address-stage outputs
   - `generate_validation_summary` — reads extraction results

2. **`00_data_quality.ipynb` required an API key**: the notebook was designed
   as a question-agnostic corpus QA notebook (pure Assess) but contained
   `from openai import OpenAI`, API key configuration, and address-phase
   constants (`LLM_MODEL`, `EXTRACTION_PROMPT`, `N_CONCERN_CLUSTERS`, etc.).

3. **Duplicate quality diagnostics**: `assess.flag_chunk_quality` and
   `assess.plot_data_quality` appeared in both `00_data_quality.ipynb` and
   `01_processing.ipynb`, with no clear ownership.

## Acceptance Criteria

- [x] `validate_extraction_cache`, `write_extraction_diagnostics`,
  `entropy_by_year`, `generate_validation_summary` live in `address.py`
- [x] `utils.py` re-exports updated to import them from `address`
- [x] `test_assess.py` updated to call moved functions via `address.*`
- [x] `00_data_quality.ipynb` requires no API key; loads `paragraph_chunks.csv`
  from disk; contains no address-phase constants
- [x] `01_processing.ipynb` has a single lightweight contamination check
  before extraction (not a duplicate of the full diagnostic)
- [x] Explicit Access→Address boundary marker present in `01_processing.ipynb`
- [x] Full test suite shows no new failures (21 pre-existing litellm failures
  unchanged; 242 passing)

## Implementation Notes

The CIP-000A split is organised around a computational cost boundary
(run-once vs run-often).  This intentionally diverges from the Fynesse AAA
epistemological boundary in `01_processing.ipynb`, where access (chunking)
and address (LLM extraction) are co-located for a deliberate safety-check
reason.  This is documented in CIP-000A's "Fynesse framework compliance"
section.

## Related

- CIP: 000A

## Progress Updates

### 2026-05-13

Task created and immediately completed. All changes committed in d6cd3a6.
CIP-000A updated with Fynesse compliance documentation (d00663e) and
status updated to In Progress (ffff629).
