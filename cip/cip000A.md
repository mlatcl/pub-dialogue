---
author: "Neil Lawrence"
created: "2026-05-12"
id: "000A"
last_updated: "2026-05-12"
status: "Proposed"
compressed: false
related_requirements: []
related_cips: ["0003"]
tags:
- cip
- notebooks
- reproducibility
- architecture
title: "Split monolithic v19 notebook into thematic analysis notebooks"
---

# CIP-000A: Split monolithic v19 notebook into thematic analysis notebooks

## Status

- [x] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

Split `public_dialogue_analyser_v19.ipynb` (~3,000 lines, 121 cells) into six
thematic notebooks separated by a clean artifact boundary on disk. Add a
`load_artifacts()` function to `dialogue_utils.py` so that all analysis
notebooks can boot entirely from pre-computed CSVs, npy arrays, and JSON
files — without calling the OpenAI API or re-running k-means.

This CIP also addresses two pre-existing gaps: entropy dicts are never saved to
disk (blocking the split), and Figure 4 reads a filename that does not match the
file actually written.

## Motivation

The v19 notebook is a single monolith that mixes:
- **Expensive one-time operations** (LLM extraction, embedding, k-means
  clustering, framing-lens identification via GPT) that take hours and incur API
  cost
- **Cheap iterative analysis** (charts, radar plots, temporal tables) that
  should be re-runnable in seconds

As written, any change to a chart forces the analyst to decide whether cached
checkpoints are still valid before re-running. A fresh-runtime execution costs
hours and significant API spend. The global-variable coupling between cells
(hundreds of cells apart) makes it fragile: moving or reordering cells breaks
hidden dependencies.

The splitting strategy separates **compute once** from **analyse often**, with
the boundary being a set of clean artifact files on disk. Analysis notebooks
never call the API; they load artifacts and produce charts.

## Detailed Description

### Notebook layout

| Notebook | Purpose | v19 cells (0-based) | API? | KMeans? |
|---|---|---|---|---|
| `00_data_quality.ipynb` | Light corpus QA — run early, run often | 3–6, then loads `paragraph_chunks.csv`, then 11–12 | no | no |
| `01_processing.ipynb` | Expensive pipeline — run once per corpus/parameter change | 3–27, 52–65, 106, 116 + new save/manifest cells | yes | yes |
| `02_shared_structure.ipynb` | Shared concerns/benefits, stable core, dendrograms | 28–29, 31–33, 48–49, 66–67, 69–71, 84–85, 87–88 | no | no |
| `03_ai_distinctiveness.ipynb` | AI vs non-AI analysis, paper Table 1/2, Figure 3 | 34–40, 72–77, 96–98 | no | no |
| `04_temporal_dynamics.ipynb` | Temporal trajectory, salience, Figure 4 | 42–46, 79–82, 99 | no | no |
| `05_robustness.ipynb` | Human validation, volatility, novelty, outputs ZIP | 93–94, 101–105, 109–115, 119 | no | no |

k-sensitivity (cells 106 and 116, re-clustering at k=60/90) moves to
`01_processing.ipynb` — it depends on the saved embeddings and is a one-time
cost that logically belongs with the other clustering work.

### Artifact boundary

`01_processing.ipynb` writes all artifacts to `OUTPUT_FOLDER` and
`CHECKPOINT_FOLDER`. Analysis notebooks (02–05) read only; they never write to
`CHECKPOINT_FOLDER` and never call the OpenAI API.

**New artifacts required** (currently missing from v19):

- `outputs/cluster_entropy.json` — `{"raw": {...}, "norm": {...}, "cross_cutting": [...]}`
- `outputs/benefit_cluster_entropy.json` — same structure for benefits

These are needed because `cluster_entropy`, `cluster_entropy_norm`, and
`cross_cutting_clusters` currently live only as in-memory globals.

**Pre-existing filename bug fixed**: `04_temporal_dynamics.ipynb` cell for
Figure 4 reads `concern_traceability_paragraphs.csv` but the file is
written as `traceability_paragraphs.csv`. Fixed to use the correct name.

### `load_artifacts()` function

Added to `dialogue_utils.py`. Takes `output_folder` and `checkpoint_folder`
as `Path` arguments; returns a single dict of all DataFrames, numpy arrays,
and JSON-derived dicts that analysis notebooks need:

```python
a = du.load_artifacts(OUTPUT_FOLDER, CHECKPOINT_FOLDER)
chunks_df    = a["chunks_df"]
concerns_df  = a["concerns_df"]
benefits_df  = a["benefits_df"]
# ... (22 keys total)
```

This eliminates the repeated merge logic
(`concerns_df.merge(chunks_df[["chunk_id", "technology_meta"]]…)`) that
currently appears multiple times in v19.

### Split script

`scripts/split_notebook.py` reads `public_dialogue_analyser_v19.ipynb` and
produces the six new notebooks by extracting the specified cell-index ranges.
It prepends a standard "load artifacts" opener cell to each analysis notebook.
The original v19 notebook is not modified or deleted (it becomes the archive
reference for Jess's methodology).

### Manifest cell

`01_processing.ipynb` ends with a manifest cell that asserts the existence of
every expected artifact and prints its row count / shape. This lets the
processing notebook fail loudly if something is missing before the analyst
switches to an analysis notebook.

## Implementation Plan

1. **Add `load_artifacts()` to `dialogue_utils.py`**
   - Implement the function loading all 22 artifact keys
   - Add `import numpy as np` to `dialogue_utils.py` top-level imports
   - Export `load_artifacts` from the module
   - Add `TestLoadArtifacts` test class in `tests/test_dialogue_utils.py`

2. **Add entropy saves to v19 (cells 20 and 58)**
   - After cell 20: write `cluster_entropy.json` with raw, norm, and cross_cutting
   - After cell 58: write `benefit_cluster_entropy.json` with same structure

3. **Fix Figure 4 filename (cell 99)**
   - Change `concern_traceability_paragraphs.csv` → `traceability_paragraphs.csv`

4. **Write `scripts/split_notebook.py`**
   - Cell-range extraction logic
   - Load-artifacts header cell generation for analysis notebooks (02–05)
   - Manifest cell generation for processing notebook

5. **Run split script** to produce the six new notebooks

6. **Add manifest cell** to `01_processing.ipynb`

7. **Run test suite** to confirm no regressions

## Backward Compatibility

- `public_dialogue_analyser_v19.ipynb` is not deleted or modified (except for the two
  entropy-save appends and the Figure 4 filename fix, which are non-breaking corrections)
- `dialogue_utils.py` gains a new exported function; existing callers are unaffected
- All existing outputs in `outputs/` remain valid; the two new JSON files are additive

## Testing Strategy

- `TestLoadArtifacts` in `tests/test_dialogue_utils.py`: creates synthetic
  artifact files in a `tmp_path` directory and verifies all 22 keys are returned
  with correct types
- Full `pytest tests/ -v` run confirms no regressions across the existing 162 tests
- Manual smoke-test: open each of the 6 new notebooks in Jupyter and confirm
  the first cell runs without error (requires artifact files in `outputs/`)

## Related Requirements

No formal requirements currently exist for notebook reproducibility; creating
this CIP is itself the design record.

## Implementation Status

- [ ] Add `load_artifacts()` to `dialogue_utils.py` + tests
- [ ] Add entropy saves to v19 cells 20 and 58
- [ ] Fix Figure 4 filename (cell 99)
- [ ] Write `scripts/split_notebook.py`
- [ ] Run split script → produce 6 notebooks
- [ ] Add manifest cell to `01_processing.ipynb`
- [ ] Run full test suite

## References

- [Original v19 strategy document](../public_dialogue_analyser_v19.ipynb)
- [CIP-0003: Extract dialogue_utils.py](cip0003.md) — prior refactor that established the shared module
- `dialogue_utils.py` — module to be extended with `load_artifacts()`
