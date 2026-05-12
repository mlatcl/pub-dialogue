---
id: "2026-05-12_resplit-01-processing"
title: "Split 01_processing into extraction and clustering notebooks"
status: "Completed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000A"]
owner: ""
dependencies: ["2026-05-12_run-split-and-add-manifest"]
tags:
- backlog
- notebook-split
- reproducibility
---

# Task: Split 01_processing into extraction and clustering notebooks

## Description

`01_processing.ipynb` produced by the initial CIP-000A split bundled three
very different cost profiles together:

- Chunking (free, local)
- LLM phrase extraction (expensive: thousands of API calls)
- Semantic embedding (OpenAI API, moderate cost)
- k-means clustering (free, CPU)
- LLM cluster labelling and framing lens identification (API, re-runnable)
- k-sensitivity re-clustering (free, CPU)

Mixing these means any change to cluster count or labelling prompt forces
re-extraction — wasting significant API spend.

The fix is to split `01_processing.ipynb` at the embedding boundary:

**`01_processing.ipynb`** — never re-run without good reason:
- Setup, ingest, chunking
- LLM concern extraction + concern embedding
- LLM benefit extraction + benefit embedding
- Extraction checkpoint cell asserting all 5 raw artifacts exist

**`01a_clustering.ipynb`** — re-run freely:
- Same setup + API key cells
- Loader cell reading saved embeddings and extracted phrases from disk
- Concern clustering, exemplars, LLM labelling, framing lenses
- Benefit clustering, exemplars, LLM labelling, framing lenses
- k=60/75/90 sensitivity analysis
- Artifact manifest

## Acceptance Criteria

- [x] `01_processing.ipynb` contains only extraction + embedding cells (26 cells)
- [x] `01a_clustering.ipynb` starts with a loader cell and contains all clustering/labelling (32 cells)
- [x] `scripts/resplit_01.py` produces both notebooks deterministically from the source
- [x] Extraction checkpoint cell at end of `01_processing.ipynb`
- [x] Artifact manifest at end of `01a_clustering.ipynb`

## Implementation Notes

`scripts/resplit_01.py` reads `01_processing.ipynb` and writes both output
notebooks. Re-run after any cell edits to keep the split in sync.

Benefit extraction cells (originally cells 31–35 in the monolith) are moved
to appear directly after concern embedding in `01_processing.ipynb`, grouping
all API extraction work together before the clustering notebook begins.

## Related

- CIP: 000A

## Progress Updates

### 2026-05-12

Task created and immediately completed. Implementation committed in df36f15.
`scripts/resplit_01.py` added to make the split reproducible.
