---
id: "2026-06-10_cip0013-generate-lens-grouping-method"
title: "Add generate_lens_grouping() method to AddressStage in pub_dialogue/address.py"
status: "Proposed"
priority: "High"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: ["2026-06-10_cip0013-canonical-file-check"]
tags:
- backlog
- framing-lenses
- sensitivity
- cip0013
---

# Task: Add generate_lens_grouping() method to AddressStage

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Extract the raw LLM lens-grouping call from `assign_framing_lenses()` into a new
public method `generate_lens_grouping()` on `AddressStage`. This method always
calls the LLM — it bypasses both the canonical-file check and the run-output
cache. It is used by the lens-scheme sensitivity analysis in `05_robustness.ipynb`
(SECTION 10D) to generate N independent lens groupings for the same cluster labels.

## Acceptance Criteria

- [ ] `AddressStage` has a `generate_lens_grouping(cluster_exemplars, cluster_labels_dict, kind, client)` method
- [ ] The method always calls the LLM regardless of what files exist on disk
- [ ] The method returns the raw `{"framing_lenses": [...]}` structure (same as the LLM response)
- [ ] `assign_framing_lenses()` delegates the LLM call to `generate_lens_grouping()` rather than duplicating the logic
- [ ] The method is callable from `05_robustness.ipynb` via `_address.generate_lens_grouping(...)`

## Implementation Notes

Factor out the existing LLM call block inside `assign_framing_lenses()` into:

```python
def generate_lens_grouping(
    self,
    cluster_exemplars: dict,
    cluster_labels_dict: dict,
    kind: str,
    client,
) -> dict:
    """Call the LLM lens-grouping step unconditionally (no cache).

    Returns the raw {"framing_lenses": [...]} response dict.
    Used by the sensitivity analysis in 05_robustness.ipynb.
    """
    # ... existing LLM prompt construction and call logic ...
```

Then in `assign_framing_lenses()`, replace the duplicated LLM block with:

```python
raw = self.generate_lens_grouping(cluster_exemplars, cluster_labels_dict, kind, client)
```

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.
