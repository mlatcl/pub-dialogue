---
id: "2026-05-12_cip000d-create-access-py"
title: "Create pub_dialogue/access.py — data access module"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: []
tags:
- backlog
- cip000d
- access-assess-address
- access
---

# Task: Create pub_dialogue/access.py — data access module

## Description

Create `pub_dialogue/access.py` as the first of three new pipeline-stage modules
implementing CIP-000D. This module encapsulates the **access** stage: getting data
into digital form. It has no dependency on any LLM or API client.

Migrate the following from `pub_dialogue/utils.py`:

- **Constants**: `MIN_CHUNK_WORDS`, `MIN_CHUNK_CHARS`, `MAX_CHUNK_WORDS`,
  `SENTENCE_FALLBACK_TARGET_WORDS`, `SENTENCE_FALLBACK_MAX_WORDS`,
  `DEFAULT_TECH_WORDS`, `_chunk_stats` dict
- `reset_chunk_stats()`
- `get_chunk_stats()`
- `_split_into_sentences()`
- `_repack_sentences_into_chunks()`
- `_extract_paragraphs_from_blocks()`
- `_paragraph_split()`
- `extract_chunks_from_pdf()` (lazy-imports `fitz`)
- `load_artifacts()`

Add `__all__` listing all public names.

## Acceptance Criteria

- [ ] `pub_dialogue/access.py` exists and is importable
- [ ] All listed functions/constants are present with original signatures intact
- [ ] `import pub_dialogue.access` succeeds with no `openai`, `litellm`, or API key required
- [ ] `from pub_dialogue.utils import extract_chunks_from_pdf` still works (backward compat via re-export in utils.py — handled in separate task)
- [ ] `__all__` defined listing public API

## Implementation Notes

The `fitz` (PyMuPDF) import inside `extract_chunks_from_pdf` should remain lazy
(inside the function body), as it is in `utils.py` today.

Do not remove function bodies from `utils.py` in this task — that is handled by
the `update-utils-py` task. This task only creates the new module.

## Related

- CIP: 000D
- Requirement: REQ-0006
- Tenet: access-assess-address

## Progress Updates

### 2026-05-12

Task created.
