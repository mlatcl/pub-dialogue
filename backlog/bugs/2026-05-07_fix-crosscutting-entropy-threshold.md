---
id: "2026-05-07_fix-crosscutting-entropy-threshold"
title: "Fix cross-cutting entropy threshold inconsistency"
status: "Ready"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
owner: ""
dependencies: []
related_cips: []
---

# Task: Fix cross-cutting entropy threshold inconsistency

## Description

The notebook classifies concern/benefit clusters as "cross-cutting" (present
across many technologies) vs. "technology-specific" using a Shannon entropy
threshold. However, the threshold value differs between the concerns and
benefits analysis sections without explanation, and neither value is documented
in the paper.

There are also two separate code paths performing this calculation — one in
the notebook directly and one via `dialogue_utils.py` — which may produce
slightly different results due to normalisation differences.

## Acceptance Criteria

- [ ] A single `is_crosscutting(cluster_distribution, threshold)` function in `dialogue_utils.py` is used in both the concerns and benefits sections
- [ ] The threshold value is defined as a named constant (`CROSSCUTTING_ENTROPY_THRESHOLD = X`) at the top of `dialogue_utils.py`
- [ ] The threshold and its rationale are documented in a comment adjacent to the constant
- [ ] Both notebook sections (concerns and benefits) pass the same threshold
- [ ] Unit test: verify a uniform-distribution cluster is classified as cross-cutting
- [ ] Unit test: verify a single-technology cluster is classified as technology-specific

## Implementation Notes

Check the current threshold values in:
- Notebook concern cross-cutting cell
- Notebook benefit cross-cutting cell
- Any existing `dialogue_utils.py` entropy code

Choose the value used in the paper's Methods section (or if not yet documented,
choose the higher (more conservative) of the two current values and document why).

## Related

- Review Issue 7 (cross-cutting threshold inconsistency)
- `dialogue_utils.py` — entropy/cross-cutting functions
- Paper Methods section (cross-cutting classification)

## Progress Updates

### 2026-05-07
Task created with Ready status based on review findings.
