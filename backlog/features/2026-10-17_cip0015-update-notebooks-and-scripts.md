---
id: "2026-10-17_cip0015-update-notebooks-and-scripts"
title: "CIP-0015: update notebooks and chunking_report for lynguine"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0015"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0015-retarget-access-stage"
tags:
- backlog
- notebooks
- lynguine
- cip0015
---

# Task: Update notebooks and scripts

## Description

Point active analysis entry points at lynguine document access:

- `01_processing.ipynb` (primary chunk extraction cell)
- `00_data_quality.ipynb` / `01a_clustering.ipynb` imports that reference the old chunker
- `scripts/chunking_report.py`

Call `segment_pdf_frame(..., strategy="pub_dialogue.v1", allowed_roots=[...])` and join `technology` / `year` from metadata after segmentation. Prefer lynguine columns (`unit_id`, `source_path`, …); derive `source_file` / `chunk_id` in the notebook only if checkpoint continuity requires it. Leave archived v12/v19 notebooks alone.

## Acceptance Criteria

- [x] Active numbered notebooks no longer import `extract_chunks_from_pdf`
- [x] Chunk extraction uses `segment_pdf_frame` (or `segment_pdf`) with explicit strategy
- [x] Metadata join is documented in the cell / adjacent markdown
- [x] `chunking_report.py` uses lynguine APIs (or is removed if obsolete)

## Implementation Notes

Default `filter_chrome=False` for parity when comparing to old artefacts; chrome opt-in is a later data decision.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
