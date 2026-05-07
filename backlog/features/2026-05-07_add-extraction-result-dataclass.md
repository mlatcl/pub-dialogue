---
id: "2026-05-07_add-extraction-result-dataclass"
title: "Add ExtractionResult dataclass and refactor extraction functions"
status: "Completed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_extract-dialogue-utils-module"]
tags:
- backlog
- extraction
- diagnostics
- dialogue-utils
---

# Task: Add ExtractionResult dataclass and refactor extraction functions

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add an `ExtractionResult` dataclass to `dialogue_utils.py` and refactor the extraction functions (`extract_concerns_from_paragraph`, `extract_benefits_from_paragraph`, or a unified `extract_phrases`) to return structured results instead of a bare list.

The key changes from the current implementation:
- Replace bare `except:` with `except Exception as e:` and store the exception message
- Track raw phrases (before tech-word filter), retained phrases (after filter), and dropped phrases separately
- Track whether the LLM returned the sentinel value (`NO_CONCERN` / `NO_BENEFIT`)

This structured return makes it possible for the next task to compute yield diagnostics.

## Acceptance Criteria

- [ ] `ExtractionResult` dataclass is defined in `dialogue_utils.py` with fields: `chunk_id` (str), `raw_phrases` (list[str]), `retained_phrases` (list[str]), `dropped_by_filter` (list[str]), `sentinel_returned` (bool), `error` (str | None)
- [ ] `extract_phrases(row_tuple, kind, client, tech_words)` (or refactored concern/benefit functions) returns `ExtractionResult` instead of `list[str]`
- [ ] No bare `except:` clause remains in any extraction function — all exceptions are caught as `except Exception as e:`
- [ ] The tech-word filter records each dropped phrase and the matching substring into `dropped_by_filter`
- [ ] `sentinel_returned` is `True` when the LLM response contains only the sentinel line and no other content
- [ ] Pytest tests cover: normal extraction returns correct `retained_phrases`; sentinel returns `sentinel_returned=True` and empty `retained_phrases`; filter drop is recorded in `dropped_by_filter`; API exception populates `error` field and returns empty `retained_phrases`
- [ ] All existing pytest tests still pass

## Implementation Notes

The `ExtractionResult` tests should use `unittest.mock.patch` to mock `client.chat.completions.create` — return a fake response with a known string to test sentinel detection, filter behaviour, and error handling without any API calls.

The unified `extract_phrases(row_tuple, kind, ...)` function uses `kind="concern"` or `kind="benefit"` to select the appropriate prompt and sentinel string. This replaces the two separate extraction functions, which will be removed from the notebook (they become thin wrappers or are deleted).

## Related

- CIP: 0001
- Documentation: [`cip/cip0001.md`](../../cip/cip0001.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_extract-dialogue-utils-module`.

### 2026-05-07 — Completed
ExtractionResult dataclass was already implemented in dialogue_utils.py (previous session).
Confirmed: chunk_id, raw_phrases, retained_phrases, dropped_by_filter, sentinel_returned, error.
