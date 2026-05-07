---
id: "2026-05-07_write-run-sensitivity-function"
title: "Write run_sensitivity function with kind parameter and separate output prefixes"
status: "Ready"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "bugs"
related_cips: ["0002"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_extract-dialogue-utils-module"]
tags:
- backlog
- sensitivity
- bug-fix
- dialogue-utils
---

# Task: Write run_sensitivity function with kind parameter and separate output prefixes

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

The notebook currently defines `run_for_k` twice — once in Part IV.A (concerns) and once in Part IV.B (benefits) — and both write to the same output file paths. In a full top-to-bottom run the benefit section overwrites concern sensitivity outputs. Plot labels in the benefit section still say "Share of all extracted concerns" (copy-paste drift never corrected).

This task writes a single `run_sensitivity(k, kind, embeddings, df, output_folder, ...)` function in `dialogue_utils.py` that replaces both definitions. All output paths and plot labels are parameterised via `kind`.

Output path scheme:
- Concern: `concern_sensitivity_stable_core_k{k}.csv`, `concern_sensitivity_fingerprint_k{k}.html`, etc.
- Benefit: `benefit_sensitivity_stable_core_k{k}.csv`, `benefit_sensitivity_fingerprint_k{k}.html`, etc.

## Acceptance Criteria

- [ ] `run_sensitivity(k, kind, embeddings, df, output_folder, ...)` is defined in `dialogue_utils.py`
- [ ] All six output file types use the prefix `f"{kind}_sensitivity_"` in their paths
- [ ] All plot titles, axis labels, and HTML headings use `kind.capitalize()` (or equivalent) — no hard-coded "concerns" in the benefit path
- [ ] A pytest test (with monkeypatching) confirms that calling with `kind="concern"` writes `concern_sensitivity_stable_core_k3.csv` and does NOT write `benefit_sensitivity_stable_core_k3.csv`, and vice versa
- [ ] The function signature is documented with a docstring listing all parameters

## Implementation Notes

Before writing the new function, diff the two existing `run_for_k` implementations side by side to identify every parameter that differs between the concern and benefit versions (embedding matrix, dataframe column names, any per-track thresholds). Document the differences in the function's docstring under a "Parameters" section.

The output folder path convention: `output_folder` is passed in (defaults to `OUTPUT_FOLDER` from the notebook config); the function itself should not hardcode any path.

This task writes the function into `dialogue_utils.py`. The next task (`2026-05-07_fix-sensitivity-call-sites-and-outputs`) updates the notebook call sites.

## Related

- CIP: 0002
- Documentation: [`cip/cip0002.md`](../../cip/cip0002.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_extract-dialogue-utils-module` (run_sensitivity lives in dialogue_utils).
