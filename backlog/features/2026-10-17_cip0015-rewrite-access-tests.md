---
id: "2026-10-17_cip0015-rewrite-access-tests"
title: "CIP-0015: rewrite access tests for lynguine cutover"
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
- tests
- cip0015
---

# Task: Rewrite access tests

## Description

Replace tests that exercise the local chunker / mocked `fitz` internals (`tests/test_access.py`, `tests/test_dialogue_utils.py` chunker sections) with tests that:

- assert `extract_chunks_from_pdf` is absent from package exports
- exercise `AccessStage` artefact loading
- optionally run one small PDF through `lynguine.access.documents.segment_pdf` with `allowed_roots`

Drop or quarantine OCR-in-chunker tests (follow-on).

## Acceptance Criteria

- [x] CI/tests no longer require the deleted local chunker
- [x] Package-export / AccessStage tests pass
- [x] At least one integration path uses lynguine segmentation (fixture or synthetic PDF)

## Implementation Notes

May depend on lynguine test fixtures or a tiny committed PDF under `tests/`.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
