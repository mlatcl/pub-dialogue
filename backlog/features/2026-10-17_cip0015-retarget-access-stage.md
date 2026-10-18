---
id: "2026-10-17_cip0015-retarget-access-stage"
title: "CIP-0015: retarget AccessStage for lynguine knobs"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0015"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0015-remove-local-pdf-chunker"
tags:
- backlog
- access
- cip0010
- cip0015
---

# Task: Retarget AccessStage

## Description

Update `AccessStage` (CIP-0010) to hold lynguine-oriented config: strategy id, aspect, `on_sparse_text`, chunk floors (`min_chunk_words`, etc.), `pdf_folder` / output paths. Remove or hard-deprecate `ocr_if_image_only`. Do not add an `extract_chunks_from_pdf` method — callers use `segment_pdf_frame` directly.

## Acceptance Criteria

- [x] `AccessStage` fields match the lynguine call pattern documented in CIP-0015
- [x] No stage method that wraps a local chunker
- [x] `load_artifacts()` still works with defaults
- [x] Module docs show the direct `segment_pdf_frame` example plus metadata join

## Implementation Notes

Keep path centralisation; implementation lives in lynguine.

## Related

- CIP: 0015
- CIP: 0010

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
