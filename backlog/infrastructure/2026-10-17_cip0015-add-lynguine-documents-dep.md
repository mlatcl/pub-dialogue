---
id: "2026-10-17_cip0015-add-lynguine-documents-dep"
title: "CIP-0015: add lynguine[documents] dependency"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "infrastructure"
related_cips: ["0015"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- lynguine
- documents
- cip0015
---

# Task: Add lynguine[documents] dependency

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add `lynguine[documents]` to `pyproject.toml` (git dependency on `lawrennd/lynguine`, optionally pinned). Verify a clean install brings in document access (`segment_pdf` / `segment_pdf_frame`). Update `SETUP.md` / README if the git dependency needs an install note. Drop the direct `PyMuPDF` dependency only when nothing in this package still imports `fitz`.

## Acceptance Criteria

- [x] `pyproject.toml` declares `lynguine[documents]`
- [x] Fresh venv install can `from lynguine.access.documents import segment_pdf_frame`
- [x] SETUP/README mention lynguine where needed for collaborators

## Implementation Notes

Prefer a pinned commit/tag once chosen; unpinned `main` is acceptable for the first cut if documented.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
