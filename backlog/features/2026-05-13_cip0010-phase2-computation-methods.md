---
id: "2026-05-13_cip0010-phase2-computation-methods"
title: "CIP-0010 Phase 2: Add AddressStage computation methods"
status: "Ready"
priority: "Medium"
created: "2026-05-13"
last_updated: "2026-05-13"
owner: ""
dependencies:
  - "2026-05-13_cip0010-phase1-stage-classes"
related_cips: ["0010"]
tags:
- backlog
- refactor
- oo-design
- stage-classes
---

# Task: CIP-0010 Phase 2 — AddressStage computation methods

## Description

Lift the analysis computation cells that were inserted into notebooks (as quick fixes) into
proper `AddressStage` methods. Replace the notebook cells with single-line method calls.

## Acceptance Criteria

- [ ] `AddressStage.concern_year_matrix(technology)` implemented — wraps
  `temporal_cluster_frequency()` (CIP-0009); used in `04_temporal_dynamics.ipynb` cells 11 and 23
- [ ] `AddressStage.benefit_year_matrix(technology)` implemented similarly
- [ ] `AddressStage.concern_trajectory(technology)` implemented — PCA 2-D trajectory logic
  currently in `04_temporal_dynamics.ipynb` cells 7–9
- [ ] `AddressStage.benefit_trajectory(technology)` implemented similarly
- [ ] `AddressStage.concern_salience()` implemented — per-technology salience logic
  currently in `03_ai_distinctiveness.ipynb`
- [ ] `AddressStage.benefit_salience()` implemented similarly
- [ ] Notebook cells replaced with single-line method calls in `03`, `04`, `05`
- [ ] Unit tests added for each method using fixture DataFrames
- [ ] `pytest tests/ -v` fully green
- [ ] Notebooks `03`, `04`, `05` execute clean via `nbconvert`

## Related

- CIP: 0010
- Depends on: Phase 1 (stage classes must exist first)
- Note: `concern_year_matrix` wraps `temporal_cluster_frequency` from CIP-0009

## Progress Updates

### 2026-05-13
Task created. Depends on Phase 1.
