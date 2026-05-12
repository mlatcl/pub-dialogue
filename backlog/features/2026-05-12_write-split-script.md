---
id: "2026-05-12_write-split-script"
title: "Write scripts/split_notebook.py to produce 6 thematic notebooks"
status: "In Progress"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000A"]
owner: ""
dependencies: ["2026-05-12_add-entropy-saves", "2026-05-12_fix-figure4-path"]
tags:
- backlog
- notebook-split
- scripts
---

# Task: Write scripts/split_notebook.py to produce 6 thematic notebooks

## Description

Write a standalone Python script that reads `public_dialogue_analyser_v19.ipynb`
and produces 6 thematic notebooks by extracting specified cell-index ranges.
Analysis notebooks (02–05) get a standard "load artifacts" opener cell prepended.
The original v19 notebook is not modified.

## Acceptance Criteria

- [ ] `scripts/split_notebook.py` created and runnable
- [ ] Produces all 6 notebooks: `00_data_quality.ipynb` through `05_robustness.ipynb`
- [ ] Each produced notebook is valid `.ipynb` JSON (kernel spec preserved)
- [ ] Analysis notebooks 02–05 have `load_artifacts()` opener cell as first code cell
- [ ] `01_processing.ipynb` has manifest cell appended as last code cell
- [ ] Original `public_dialogue_analyser_v19.ipynb` unchanged after run

## Implementation Notes

Cell ranges (0-based, inclusive):
```python
SPLITS = {
    "00_data_quality.ipynb":       [(3, 6), (11, 12)],
    "01_processing.ipynb":         [(3, 29), (52, 65), (106, 106), (116, 116)],
    "02_shared_structure.ipynb":   [(28, 29), (31, 33), (48, 49),
                                    (66, 67), (69, 71), (84, 85), (87, 88)],
    "03_ai_distinctiveness.ipynb": [(34, 40), (72, 77), (96, 98)],
    "04_temporal_dynamics.ipynb":  [(42, 46), (79, 82), (99, 99)],
    "05_robustness.ipynb":         [(93, 94), (101, 105), (109, 115), (119, 119)],
}
```

Script should use `argparse` so source/dest can be overridden; default reads
`public_dialogue_analyser_v19.ipynb` and writes notebooks to repo root.

## Related

- CIP: 000A

## Progress Updates

### 2026-05-12

Task created. In Progress — implementing as part of CIP-000A notebook split.
