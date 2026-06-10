---
id: "2026-06-10_cip0013-run-section-10d-and-record"
title: "Run Section 10D in 05_robustness.ipynb and record direction-consistency result"
status: "Proposed"
priority: "Medium"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: ["2026-06-10_cip0013-add-section-10d-robustness", "2026-06-10_cip0013-generate-and-commit-canonical-files"]
tags:
- backlog
- framing-lenses
- sensitivity
- cip0013
---

# Task: Run Section 10D and record direction-consistency result

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Execute the SECTION 10D code cell in `05_robustness.ipynb` and fill in the
result line in the markdown cell. This provides the M6(e) evidence cited in the
paper's robustness section.

## Acceptance Criteria

- [ ] Section 10D code cell runs to completion without errors
- [ ] `outputs/lens_sensitivity_summary.csv` exists with 5 rows
- [ ] `outputs/lens_sensitivity_all_runs.csv` exists
- [ ] The markdown cell `**Result (M6e)**` line is filled in with the actual
      direction-consistency count and pp range
- [ ] The filled-in result is committed to the notebook

## Implementation Notes

The result line to fill in (in the Section 10D markdown cell):

```
**Result (M6e)**: Direction consistent in X/5 runs; pp range Y.Y to Z.Z
```

If direction is inconsistent (< 4/5 runs), this is a significant finding that
should feed back into the paper narrative — flag it and do not simply omit it.

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.
