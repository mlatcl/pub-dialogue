---
id: "2026-05-07_remove-missing-source-text-cluster"
title: "Remove or guard against 'Missing source text' cluster artefact"
status: "Ready"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
owner: ""
dependencies: []
related_cips: []
---

# Task: Remove or guard against 'Missing source text' cluster artefact

## Description

Some rows in the phrases DataFrame have a missing or empty source text field
(`chunk_text` is NaN or empty string). These rows appear as a cluster in the
analysis labelled something like "Missing source text" or with an empty label.
This is a data quality artefact, not a genuine participant concern or benefit.

The phrases should never enter the embedding or clustering pipeline with missing
source text. They need to be filtered out upstream.

## Acceptance Criteria

- [ ] Before the embedding step, filter out any phrases where `chunk_text` is NaN or empty
- [ ] The filter reports how many rows were dropped (log or print statement)
- [ ] A unit test confirms that rows with `chunk_text = NaN` or `chunk_text = ""` are excluded
- [ ] No "Missing source text" cluster appears in the output

## Implementation Notes

In the notebook's embedding cell (or in `dialogue_utils.py` before calling
`get_embeddings_batch`), add:

```python
mask_missing = phrases_df['chunk_text'].isna() | (phrases_df['chunk_text'].str.strip() == '')
n_missing = mask_missing.sum()
if n_missing > 0:
    print(f"[WARN] Dropping {n_missing} phrases with missing source text")
    phrases_df = phrases_df[~mask_missing].copy()
```

Investigate *why* these rows have missing source text — it may be related to
the chunking bug fixed in CIP-0006 (sub-threshold fragments whose text field is
not populated).

## Related

- Review Issue 9 (missing source text cluster)
- CIP-0006 (chunking fix — may resolve the root cause)
- `dialogue_utils.py` — `get_embeddings_batch`, `run_sensitivity`
- Notebook embedding cells

## Progress Updates

### 2026-05-07
Task created with Ready status based on review findings.
