---
id: "2026-10-17_cip0015-remove-local-pdf-chunker"
title: "CIP-0015: remove local PDF chunker from access.py"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0015"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0015-add-lynguine-documents-dep"
tags:
- backlog
- access
- lynguine
- cip0015
---

# Task: Remove local PDF chunker

## Description

Delete `extract_chunks_from_pdf` and its helpers from `pub_dialogue/access.py` (`_extract_paragraphs_from_blocks`, `_paragraph_split`, `_split_into_sentences`, `_repack_sentences_into_chunks`, `_coverage`, `_word_count`, `_ocr_text`, chunk-stats / `_doc_diagnostics` unless still needed by a rewritten report). Remove re-exports from `pub_dialogue/__init__.py` and `pub_dialogue/utils.py`. No compatibility shim.

## Acceptance Criteria

- [x] `extract_chunks_from_pdf` is not defined or re-exported by the package
- [x] Chunking helpers and OCR-in-chunker path are gone from `access.py`
- [x] Module docstring describes lynguine as the PDF access path
- [x] `load_artifacts` / checkpoint I/O remain

## Implementation Notes

Breaking change by design (CIP-0015). OCR is a follow-on, not reintroduced here.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0015 acceptance.

### 2026-10-17 (later)

Implementation completed as part of CIP-0015 cutover.
