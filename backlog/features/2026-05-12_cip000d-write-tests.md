---
id: "2026-05-12_cip000d-write-tests"
title: "Add tests for access.py and assess.py; verify full test suite passes"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: [
  "2026-05-12_cip000d-update-utils-py",
  "2026-05-12_cip000d-update-init-py"
]
tags:
- backlog
- cip000d
- testing
- access-assess-address
---

# Task: Add tests for access.py and assess.py; verify full test suite passes

## Description

Add `tests/test_access.py` and `tests/test_assess.py`. Extend existing tests
to cover backward-compatibility of re-exports. Run the full test suite to
confirm no regressions.

### `tests/test_access.py`

- Import `pub_dialogue.access` with no API key set — must not raise
- Test `_looks_like_bibliography` / `_looks_like_table_row` equivalents for
  access-stage helpers
- Test `load_artifacts` with `tmp_path` fixtures (create synthetic CSV/npy/json
  files and assert all 22 keys are returned with correct types)
- Test `extract_chunks_from_pdf` with a minimal synthetic PDF created via fitz
  (or mock fitz if environment lacks it)

### `tests/test_assess.py`

- Import `pub_dialogue.assess` with no `OPENAI_API_KEY` set — must not raise
  (key assertion for the no-LLM contract)
- Test `_looks_like_bibliography` with strings that should/should not match
- Test `_looks_like_table_row` with sample strings
- Test `plot_data_quality` with a minimal synthetic `chunks_df` — assert PNG
  is written to `tmp_path`
- Test `flag_chunk_quality` with a minimal `chunks_df` — assert CSV is written
  to `tmp_path` with expected columns

### Backward-compatibility tests (extend existing or add to `test_dialogue_utils.py`)

- `from pub_dialogue.utils import extract_chunks_from_pdf` — assert it is the
  same object as `pub_dialogue.access.extract_chunks_from_pdf`
- `from pub_dialogue.utils import ExtractionResult` — assert importable and
  is same as `pub_dialogue.address.ExtractionResult`
- `from pub_dialogue.utils import plot_data_quality` — assert importable

## Acceptance Criteria

- [ ] `tests/test_access.py` exists with ≥ 3 passing tests
- [ ] `tests/test_assess.py` exists with ≥ 4 passing tests including the no-API-key import test
- [ ] Backward-compat tests pass
- [ ] `pytest tests/ -v` shows zero failures

## Implementation Notes

The no-API-key import test for `assess.py` is critical: it enforces the tenet
that assess work is question-agnostic and requires no LLM. Set
`os.environ.pop("OPENAI_API_KEY", None)` before the import assertion if needed.

## Related

- CIP: 000D
- Requirement: REQ-0006

## Progress Updates

### 2026-05-12

Task created.
