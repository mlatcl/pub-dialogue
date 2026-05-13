---
id: "2026-05-13_cip000F-pilot-00-data-quality"
title: "CIP-000F Pilot: Refactor imports in 00_data_quality.ipynb"
status: "Completed"
priority: "High"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000F"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- notebooks
- imports
- refactoring
---

# Task: CIP-000F Pilot — Refactor imports in 00_data_quality.ipynb

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Pilot refactor of `00_data_quality.ipynb` to follow the lazy, co-located import convention (CIP-000F). The notebook currently has a monolithic import cell (Cell 3) with ~22 imports from stdlib, sklearn, scipy, matplotlib, plotly, openai, tqdm, fitz, and others. Each import should be moved into a small cell placed immediately above the cell that first uses it.

Only the following may remain in the setup cell: `os`, `json`, `Path`, `pandas`, `numpy`.

## Acceptance Criteria

- [x] Monolithic import cell is eliminated (or reduced to setup-cell-permitted imports only)
- [x] Every non-setup import has its own cell immediately above its first-use cell
- [x] Notebook executes top-to-bottom without `ImportError` or `NameError`
- [ ] Cell outputs are consistent with the pre-refactor version (requires Colab/API run)

## Implementation Notes

Map each import in Cell 3 to the first cell in the notebook that uses it, then insert a new code cell immediately before that cell. Work section by section to keep the mapping tractable.

## Related

- CIP: 000F
- PRs: —
- Documentation: `.cursor/rules/notebook_imports.mdc`

## Progress Updates

### 2026-05-13

Task created. Pilot selected as first step before rolling out to remaining notebooks.
