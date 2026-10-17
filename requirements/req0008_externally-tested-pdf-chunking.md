---
id: "0008"
title: "PDF chunking is provided by an externally tested document-access dependency"
status: "Implemented"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
related_tenets: ["access-assess-address"]
stakeholders: ["Neil Lawrence"]
tags: ["pipeline", "access", "chunking", "documents", "reusability"]
---

# REQ-0008: PDF chunking is provided by an externally tested document-access dependency

## Description

Active analyses must obtain PDF text units from a shared document-access dependency whose chunking behaviour is versioned and tested outside this package. The `pub_dialogue` package must not maintain its own PDF segmentation implementation.

Research labels (for example technology and year) remain analysis concerns: they are joined after units are produced, not embedded in the chunker. Sparse or image-only PDFs are surfaced honestly for quality work rather than hidden behind a second, package-local OCR chunking path.

**Why this matters**: A second in-tree chunker drifts from the shared contract and doubles maintenance. External ownership of the algorithm means parity and regressions are covered where the chunker lives, while this analysis package focuses on assess and address.

**Who benefits**: Maintainers of pub-dialogue and related analyses that share the same PDF access path; collaborators who install one documents dependency and get the same units.

## Acceptance Criteria

- [x] Active notebooks and scripts obtain PDF text units from an installed external document-access dependency, not from local segmentation helpers in `pub_dialogue.access`
- [x] That dependency’s chunking path has its own tests upstream; this repository does not re-own or re-implement the chunking algorithm
- [x] Research metadata used by this analysis is joined after units are produced
- [x] Package tests cover integration and contract (import, call, join / stage config), not a duplicate of the chunker

## Notes

This requirement states the outcome (externally tested chunking, no package-local algorithm). Which library, strategy name, or column schema is chosen belongs in the CIP that implements it.

OCR of image-only PDFs is out of scope for the acceptance criteria above; it may be a follow-on preprocess or an upstream strategy, but must not reintroduce a second chunker inside `pub_dialogue.access`.

## References

- **Related Tenets**: [access-assess-address](../tenets/pub-dialogue/access-assess-address.md)
- **Related CIP**: [CIP-0015](../cip/cip0015.md)

## Progress Updates

### 2026-10-17
Requirement created to ground CIP-0015. Status set to In Progress with CIP-0015 implementation.

### 2026-10-17 (later)
CIP-0015 implemented: local chunker removed; active notebooks/scripts call lynguine `segment_pdf_frame`; `tests/test_access.py` covers contract/integration. Status → Implemented (validation / CIP close still open).
