---
id: "2026-05-07_refactor-notebook-imports-strip-outputs"
title: "Refactor notebook to use dialogue_utils, strip outputs, align section numbering"
status: "Ready"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "infrastructure"
related_cips: ["0003"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_extract-dialogue-utils-module"]
tags:
- backlog
- refactoring
- notebook
- nbstripout
---

# Task: Refactor notebook to use dialogue_utils, strip outputs, align section numbering

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Once `dialogue_utils.py` and its test suite exist (previous task), update the notebook itself:

1. Replace all inline function definitions with `import dialogue_utils as du` and calls to `du.<function>(...)`
2. Update SECTION 0 to make `dialogue_utils.py` available in Colab (add to upload zip; add `sys.path.insert(0, '/content')`)
3. Install and configure `nbstripout` so stored cell outputs are never committed
4. Update section numbering to a single consistent scheme and add a Table of Contents markdown cell

## Acceptance Criteria

- [ ] Notebook SECTION 0 includes `import dialogue_utils as du` after path setup
- [ ] No inline `def` statement in the notebook duplicates a function in `dialogue_utils.py`
- [ ] `nbstripout` is installed as a git filter (`nbstripout --install`) and recorded in a `requirements-dev.txt` or setup note in the README
- [ ] Committed `.ipynb` file size is < 500 KB (verify with `wc -c`)
- [ ] Section numbering follows the scheme defined in CIP-0003: SECTION 0, SECTION 1, PART I–V with consistent sub-labels
- [ ] A Table of Contents markdown cell appears immediately after the SECTION 0 setup cell
- [ ] A markdown cell near the top of the notebook lists all functions available from `du` with one-line descriptions
- [ ] Running the notebook end-to-end from checkpoints produces `cluster_summary.csv` byte-identical to the pre-refactor version (or documents any expected numerical differences)

## Implementation Notes

Work cell-by-cell through the notebook. For each `def` statement that matches a function in `dialogue_utils.py`, delete the definition and replace any calls in that cell with `du.<function>(...)`.

Some cells may have local one-off lambdas or inline helpers that are genuinely cell-specific — leave those in place.

The Colab upload pattern: the existing cell that calls `google.colab.files.upload()` for the PDFs zip should be extended to also upload `dialogue_utils.py` (or it can be bundled into the zip). After upload/unzip, add:

```python
import sys
sys.path.insert(0, '/content')
import dialogue_utils as du
```

## Related

- CIP: 0003
- Documentation: [`cip/cip0003.md`](../../cip/cip0003.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_extract-dialogue-utils-module`.
