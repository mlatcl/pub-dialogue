---
author: "Neil Lawrence"
created: "2026-05-13"
id: "000F"
last_updated: "2026-05-13"
status: "Closed"
compressed: true
related_requirements: []
related_cips: []
tags:
- cip
- notebooks
- imports
- refactoring
title: "Refactor Notebook Imports to Lazy, Co-located Style"
---

# CIP-000F: Refactor Notebook Imports to Lazy, Co-located Style

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [x] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

Refactor all analysis notebooks (`00_data_quality.ipynb` through `05_robustness.ipynb`) to follow the lazy, co-located import convention documented in `.cursor/rules/notebook_imports.mdc`. Currently, notebooks collect all imports in a single monolithic cell near the top. Each import should instead live in its own cell placed immediately above the cell that first uses it.

## Motivation

Notebooks are executed top-to-bottom one cell at a time. A heavy monolithic import block at the top (e.g., loading `sklearn`, `umap`, `matplotlib`, `plotly`, `scipy`, `fitz`, `openai`, `tqdm`) slows every re-run even when only a small portion of the notebook is being re-executed. This friction increases iteration time during analysis.

Co-locating imports directly above their first use site also makes sections self-contained and readable: a reader can jump to any section of the notebook and immediately see what that section depends on, without needing to scroll to the top. This is especially important for research notebooks where sections are frequently run independently.

The current notebooks (e.g., `00_data_quality.ipynb` Cell 3) aggregate 20+ imports from stdlib, pandas/numpy, sklearn, scipy, matplotlib, plotly, openai, tqdm, and project-local packages into a single block, violating this principle.

## Detailed Description

### Convention Summary (from `.cursor/rules/notebook_imports.mdc`)

**Co-located imports**: each import (or group of imports for the same library) lives in its own cell placed immediately above the cell that first needs it.

**Setup cell exception**: the project-wide setup cell (which installs packages, sets `_REPO_ROOT`, `OUTPUT_FOLDER`, etc.) may retain a small set of universally-used stdlib/project modules:
- `import os, json`
- `from pathlib import Path`
- `import pandas as pd`
- `import numpy as np`

All other imports — especially heavy third-party libraries (`sklearn`, `umap`, `matplotlib`, `concurrent.futures`, `litellm`, `fitz`, `openai`, `plotly`, `scipy`, `seaborn`, `tqdm`, etc.) — must move to sit directly above their first use cell.

### Notebooks in scope

| Notebook | Status |
|---|---|
| `00_data_quality.ipynb` | Pilot / test case |
| `01_processing.ipynb` | To be done |
| `01a_clustering.ipynb` | To be done |
| `02_shared_structure.ipynb` | To be done |
| `03_ai_distinctiveness.ipynb` | To be done |
| `04_temporal_dynamics.ipynb` | To be done |
| `05_robustness.ipynb` | To be done |

### Approach for each notebook

1. Identify the monolithic import cell(s).
2. Determine which imports belong in the setup cell (stdlib universals + pandas/numpy only).
3. For each remaining import, find the earliest cell that uses it.
4. Insert a new code cell immediately before that first-use cell containing only those imports.
5. Remove the moved imports from the original monolithic import cell (deleting it entirely if it becomes empty).
6. Run the notebook top-to-bottom to verify no `NameError` or `ImportError` occurs.

## Implementation Plan

1. **Pilot on `00_data_quality.ipynb`**:
   - Audit all import cells and map each import to its first-use cell.
   - Decide which imports stay in the setup cell.
   - Insert co-located import cells above each first-use site.
   - Delete or trim the monolithic import cell.
   - Verify by running the notebook.

2. **Apply to `01_processing.ipynb`**:
   - Same process as above.

3. **Apply to `01a_clustering.ipynb`**:
   - Same process as above.

4. **Apply to `02_shared_structure.ipynb`**:
   - Same process as above.

5. **Apply to `03_ai_distinctiveness.ipynb`**:
   - Same process as above.

6. **Apply to `04_temporal_dynamics.ipynb`**:
   - Same process as above.

7. **Apply to `05_robustness.ipynb`**:
   - Same process as above.

## Backward Compatibility

This is a pure structural refactor with no change to logic. Notebooks that are run top-to-bottom (the normal usage) will behave identically. The only risk is if a user was relying on an early import cell to make a symbol available before running a later section in isolation — but such usage is undocumented and the new structure is strictly cleaner.

## Testing Strategy

- After each notebook is refactored, execute all cells via `jupyter nbconvert --to notebook --execute` and confirm zero errors.
- Check that cell outputs remain identical to the pre-refactor run (or are consistent with any expected non-determinism such as LLM calls).

## Related Requirements

No formal requirements exist yet for notebook style. This CIP operationalises the existing cursor rule (`.cursor/rules/notebook_imports.mdc`).

## Implementation Status

- [x] Pilot refactor: `00_data_quality.ipynb`
- [x] Refactor: `01_processing.ipynb`
- [x] Refactor: `01a_clustering.ipynb`
- [x] Refactor: `02_shared_structure.ipynb` — already co-located; no changes needed
- [x] Refactor: `03_ai_distinctiveness.ipynb` — already co-located; no changes needed
- [x] Refactor: `04_temporal_dynamics.ipynb` — already co-located; no changes needed
- [x] Refactor: `05_robustness.ipynb` — already co-located; no changes needed

## References

- `.cursor/rules/notebook_imports.mdc` — the convention this CIP operationalises
