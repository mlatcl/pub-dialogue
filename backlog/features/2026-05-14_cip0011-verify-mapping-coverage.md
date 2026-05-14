---
id: "2026-05-14_cip0011-verify-mapping-coverage"
title: "Re-run notebook cell mapping audit and verify no substantive gaps remain"
status: "Proposed"
priority: "Low"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0011"]
owner: ""
dependencies:
  - "2026-05-14_cip0011-group-a-data-quality-cell"
  - "2026-05-14_cip0011-group-b-cross-tech-heatmap"
  - "2026-05-14_cip0011-group-c-volume-top-clusters"
  - "2026-05-14_cip0011-group-d-robustness-cells"
  - "2026-05-14_cip0011-group-e-evidence-pack-export"
tags:
- backlog
- verification
---

# Task: Re-run notebook cell mapping audit and verify no substantive gaps remain

## Description

After all Groups A–E are implemented, re-run the `notebook_cell_mapping.json` generator
script to confirm that remaining `no_match` cells are limited to legitimate
infrastructure-only differences between `main-version.ipynb` and the numbered notebooks.

## Acceptance Criteria

- [ ] Run the mapping script against the updated numbered notebooks
- [ ] All `no_match` cells are accounted for as one of:
  - Infrastructure/setup (pip install, Colab file upload, raw API key config)
  - Cells intentionally dropped because their logic moved entirely into the library
    (e.g. inline LLM extraction, inline clustering) — these are correctly handled by the
    corresponding address-phase function
- [ ] Zero substantive analysis or visualisation cells remain unmatched
- [ ] Update `notebook_cell_mapping.json` in the repo with the post-implementation results
- [ ] Update CIP-0011 status to Implemented

## Implementation Notes

The mapping script is the inline Python in the session history. Extract it to
`scripts/check_notebook_coverage.py` as part of this task so the check can be re-run
easily in future.

## Related

- CIP: 0011
- `notebook_cell_mapping.json` — original audit artefact

## Progress Updates

### 2026-05-14
Task created. Depends on all five implementation groups completing first.
