---
id: "2026-05-07_reconcile-notebook-narrative"
title: "Reconcile notebook narrative with paper numbers"
status: "Ready"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
owner: ""
dependencies:
  - "2026-05-07_fix-chunk-filter-and-cache (CIP-0006)"
related_cips: ["0006"]
---

# Task: Reconcile notebook narrative with paper numbers

## Description

Several numbers in the notebook's markdown cells are inconsistent with each
other and with the paper draft:

1. **Paragraph yield**: The notebook reports "~15% of paragraphs yielded a
   concern phrase." The actual figure is 7.2% (899 concerns from 12,528 chunks).
   The 14.5% figure counts concern phrases per chunk, not chunks yielding ≥1
   concern.

2. **Document count**: "41 of 66 documents produced zero concerns" — this
   should be re-checked after the cache fix (CIP-0006), as some may be
   cache-masked API failures.

3. **Cluster membership counts**: Cluster sizes in the sensitivity charts
   (`k`-sensitivity) differ from the cluster counts in the main analysis cells
   due to resampling in `run_sensitivity`. The notebook does not flag this.

4. **Year labels**: Temporal chart axis labels include years that do not match
   the metadata year for some documents (issue introduced when year is extracted
   by regex from filename).

All markdown narrative cells in the notebook should be audited and updated to
match the actual computed values.

## Acceptance Criteria

- [ ] Yield percentage corrected in all notebook narrative cells: `X% of substantive paragraphs (≥50 words) yielded ≥1 concern/benefit phrase`
- [ ] 41-of-66 figure re-verified or corrected after CIP-0006
- [ ] Cluster count discrepancy between sensitivity analysis and main analysis is explained in a comment
- [ ] Temporal chart year labels verified against metadata year field
- [ ] Paper draft updated to match corrected notebook narrative

## Implementation Notes

Do this pass *after* CIP-0006 is implemented, since the chunk counts will
change. Use `whats-next` to track dependency.

## Related

- Review Issue 3 (chunk count impact on paper)
- Review Issue 11 (narrative inconsistency)
- CIP-0006 (must be completed first — changes corpus counts)
- Paper draft narrative sections

## Progress Updates

### 2026-05-07
Task created with Ready status. Depends on CIP-0006 implementation.
