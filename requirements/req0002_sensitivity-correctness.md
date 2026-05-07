---
id: "0002"
title: "Concern and benefit sensitivity outputs are distinct and non-overwriting"
status: "Proposed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
related_tenets: []
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["sensitivity", "concerns", "benefits", "outputs", "reproducibility"]
---

# REQ-0002: Concern and benefit sensitivity outputs are distinct and non-overwriting

## Description

The sensitivity analysis (PART IV of the notebook) tests robustness to cluster count by running the analysis at k ∈ {60, 75, 90}. It does this separately for concerns (Part IV.A) and benefits (Part IV.B). However, both sections define a function called `run_for_k` and write outputs to the same file paths (e.g. `sensitivity_stable_core_k75.csv`). In a full top-to-bottom run, the benefit section overwrites the concern section's files, leaving only benefit-derived sensitivity outputs on disk under concern-named paths.

The `outputs/` folder contains `benefit_sensitivity_*` files whose names differ from the paths written by the notebook, suggesting they were created by manual renaming rather than a code fix. Plot labels in the benefit section also still read "Share of all extracted concerns" — a sign of copy-paste drift that has not been corrected.

The requirement is that concern and benefit sensitivity outputs should be independent, clearly labelled, and never at risk of overwriting each other, regardless of execution order.

**Why this matters**: If the sensitivity outputs cannot be trusted to correspond to the correct analysis track, robustness claims in any resulting paper are invalid. Reproducibility is a core requirement for publishable research.

**Who benefits**: Neil, Jess, and any reader assessing the robustness of the methodology.

## Acceptance Criteria

- [ ] Concern sensitivity outputs use the prefix `concern_sensitivity_` (e.g. `concern_sensitivity_stable_core_k75.csv`)
- [ ] Benefit sensitivity outputs use the prefix `benefit_sensitivity_` (e.g. `benefit_sensitivity_stable_core_k75.csv`)
- [ ] No concern output file path is identical to any benefit output file path
- [ ] Plot labels in the benefit sensitivity section correctly refer to "benefits" not "concerns"
- [ ] A full top-to-bottom notebook run produces both complete concern and benefit sensitivity files without either overwriting the other
- [ ] The sensitivity outputs in `outputs/` match those written by the notebook without manual renaming

## Notes

This requirement does not mandate a specific implementation (e.g. a single parameterised function vs two separate functions). That design choice belongs in the corresponding CIP.

## References

- **Related Tenets**: (none defined yet for this project)
- **External Links**: See `public_dialogue_analyser_v12b_4.ipynb` cells 104 (Part IV.A) and 114 (Part IV.B)

## Progress Updates

### 2026-05-07
Requirement proposed based on code analysis confirming the `run_for_k` overwrite issue and copy-paste drift in plot labels.
