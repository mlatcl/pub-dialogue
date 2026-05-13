---
id: "2026-05-13_extraction-test-mode"
title: "Add TEST_MODE for small-scale extraction validation"
status: "Proposed"
priority: "Medium"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000E"]
owner: ""
dependencies: []
tags:
- testing
- extraction
- notebook
---

# Task: Add TEST_MODE for small-scale extraction validation

## Description

There is no way to quickly validate the extraction pipeline end-to-end without
committing to a full 10,000-chunk, multi-hour run. Debugging issues (wrong API key,
broken imports, bad prompts) requires waiting through the entire corpus.

Add `TEST_MODE` / `TEST_N_DOCS` constants to `01_processing.ipynb` that limit
extraction to a small sample of source documents, enabling a ~1-minute validation
pass.

## Acceptance Criteria

- [ ] `TEST_MODE = False` constant added near the top of `01_processing.ipynb` (in the config cell)
- [ ] `TEST_N_DOCS = 3` constant added alongside it
- [ ] A filter cell (immediately before the extraction cell) subsets `chunks_df` to the first `TEST_N_DOCS` source files when `TEST_MODE=True`
- [ ] Test mode prints a visible warning: `"⚠️ TEST_MODE active — using {n} chunks from {k} documents"`
- [ ] Test mode uses a separate cache path (`extracted_concerns_test.json`) so it never pollutes the full-run cache
- [ ] Benefits extraction cell has the same test-mode gate
- [ ] Notebook validation cell checks `TEST_MODE` and warns if outputs look suspiciously small

## Implementation Notes

In the config cell:
```python
TEST_MODE = False    # Set True for a quick end-to-end validation run
TEST_N_DOCS = 3      # Number of source documents to use in test mode
```

Filter cell (before extraction):
```python
if TEST_MODE:
    _test_docs = chunks_df["source_file"].unique()[:TEST_N_DOCS]
    chunks_df = chunks_df[chunks_df["source_file"].isin(_test_docs)].copy()
    show_warning(f"TEST_MODE active — {len(chunks_df)} chunks from {len(_test_docs)} documents")
    concerns_cache_file = CHECKPOINT_FOLDER / "extracted_concerns_test.json"
```

## Related

- CIP: 000E

## Progress Updates

### 2026-05-13
Task created following inability to quickly diagnose extraction failures on full corpus.
