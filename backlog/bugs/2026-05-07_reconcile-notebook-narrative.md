---
id: "2026-05-07_reconcile-notebook-narrative"
title: "Reconcile notebook narrative with paper numbers"
status: "In Progress"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-13"
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

- [x] Yield percentage corrected: v19 corpus has 10,047 chunks; 65.1% yield ≥1 concern, 26.6% yield ≥1 benefit
- [x] Document count corrected to 66 (not 65) in 01_processing.ipynb and 00_data_quality.ipynb
- [x] "41 of 66 docs zero concerns" resolved: v19 re-extraction shows only 2 of 66 docs have zero concerns (64/66 have ≥1 concern; 65/66 have ≥1 benefit)
- [ ] Cluster count discrepancy between sensitivity analysis and main analysis explained in a comment
- [ ] Temporal chart year labels verified against metadata year field (note: 2004/2007/2008/2009/2010 appear — verify vs metadata)
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

### 2026-05-13
CIP-0006 confirmed closed. Computed ground-truth numbers from v19 outputs:
- Total chunks: 10,047 (7,870 ≥50 words; 2,177 <50 words)
- Total documents: 66
- Concern phrases: 19,384 across 6,542 chunks (65.1%) from 64 documents
- Benefit phrases: 7,815 across 2,671 chunks (26.6%) from 65 documents
- AI corpus: 41 docs, 4,784 chunks, 9,780 concern phrases, 100% doc yield
- Fixed "65 documents" → "66 documents" in 01_processing.ipynb and 00_data_quality.ipynb
- Remaining: temporal year label audit and paper draft update
