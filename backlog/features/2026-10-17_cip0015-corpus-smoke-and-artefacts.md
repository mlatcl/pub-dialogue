---
id: "2026-10-17_cip0015-corpus-smoke-and-artefacts"
title: "CIP-0015: corpus smoke and artefact regeneration decision"
status: "Completed"
priority: "Medium"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0015"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0015-update-notebooks-and-scripts"
- "2026-10-17_cip0015-rewrite-access-tests"
tags:
- backlog
- smoke
- cip0015
---

# Task: Corpus smoke and artefacts

## Description

Run lynguine `pub_dialogue.v1` over the local PDF corpus (`pdfs/` / `data/`) under parity settings (`filter_chrome=False`). Compare unit counts / chunking_method mix to a previous baseline if available. Decide whether to regenerate `outputs/paragraph_chunks.csv` (and related checkpoints) in this change or document a follow-on regeneration pass. Note sparse/OCR PDFs under `on_sparse_text` policy.

## Acceptance Criteria

- [x] Smoke run completes on the available corpus (or documents blockers)
- [x] Brief note of count deltas vs old chunker (if baseline exists)
- [x] Explicit decision: regenerate artefacts now vs later
- [x] Sparse/image-only PDFs listed with chosen `on_sparse_text` behaviour

## Implementation Notes

Do not block CIP close on full LLM re-extraction; access-layer smoke is enough.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
