---
id: "2026-05-13_cip000F-refactor-01-processing"
title: "CIP-000F: Refactor imports in 01_processing.ipynb"
status: "Proposed"
priority: "Medium"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000F"]
owner: "Neil Lawrence"
dependencies: ["2026-05-13_cip000F-pilot-00-data-quality"]
tags:
- backlog
- notebooks
- imports
- refactoring
---

# Task: CIP-000F — Refactor imports in 01_processing.ipynb

## Description

Refactor `01_processing.ipynb` to follow the lazy, co-located import convention (CIP-000F), following the same approach validated in the pilot task on `00_data_quality.ipynb`.

## Acceptance Criteria

- [ ] Monolithic import cell(s) eliminated or reduced to setup-cell-permitted imports only
- [ ] Every non-setup import has its own cell immediately above its first-use cell
- [ ] Notebook executes top-to-bottom without `ImportError` or `NameError`

## Related

- CIP: 000F
- Documentation: `.cursor/rules/notebook_imports.mdc`

## Progress Updates

### 2026-05-13

Task created as part of CIP-000F rollout plan.
