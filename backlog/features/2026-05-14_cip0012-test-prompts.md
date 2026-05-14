---
id: "2026-05-14_cip0012-test-prompts"
title: "Add tests/test_prompts.py and verify existing test suite passes"
status: "Proposed"
priority: "Medium"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0012"]
owner: ""
dependencies: ["2026-05-14_cip0012-load-prompts-and-wire"]
tags:
- backlog
- prompts
- tests
- cip0012
---

# Task: Add tests/test_prompts.py and verify existing suite passes

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add a dedicated test file `tests/test_prompts.py` covering the new prompt
loading machinery, and confirm that all pre-existing tests in
`tests/test_address.py` continue to pass without modification.

**Tests to add in `tests/test_prompts.py`:**

1. **Default load** — `load_prompts()` returns a dict with the expected top-level
   keys (`extraction`, `system_messages`).
2. **Concern variants** — the returned dict contains `A_current`, `B_paraphrase`,
   `C_minimal` under `extraction.concern`, each containing `{text}`.
3. **Benefit variants** — same structure under `extraction.benefit`.
4. **Default key** — `extraction.concern.default` and `extraction.benefit.default`
   are both `"A_current"`.
5. **System messages** — `system_messages.qualitative_researcher` and
   `system_messages.engagement_analyst` are non-empty strings.
6. **Constants match YAML** — `EXTRACTION_PROMPT` equals
   `load_prompts()["extraction"]["concern"]["A_current"]` (round-trip check).
7. **Variant dicts match YAML** — `CONCERN_PROMPT_VARIANTS` keys equal the
   non-`default` keys under `extraction.concern`.
8. **Missing file fallback** — `load_prompts(path=Path("/nonexistent.yml"))`
   does not raise and returns a dict with `EXTRACTION_PROMPT` text as the
   concern `A_current` value.
9. **Custom path injection** — `load_prompts(path=tmp_path / "custom.yml")`
   loads from the given path when it exists (use `pytest` `tmp_path` fixture
   with a minimal valid YAML).

## Acceptance Criteria

- [ ] `tests/test_prompts.py` exists with tests covering points 1–9 above
- [ ] All nine tests pass with `pytest tests/test_prompts.py -v`
- [ ] `pytest tests/test_address.py -v` passes with no failures or new skips
- [ ] `pytest tests/` passes overall (no regressions anywhere)

## Implementation Notes

Use `pytest` with `tmp_path` for the custom-path test. No mocking of file I/O
is needed — the real `prompts.yml` should be loadable in the test environment
since tests run from the repo root.

For the missing-file fallback test, check both that no exception is raised and
that the returned dict contains the expected fallback text (not an empty dict).
Use `pytest.warns` or check log output to assert the warning is emitted.

## Related

- CIP: 0012
- PRs:
- Documentation:

## Progress Updates

### 2026-05-14

Task created following acceptance of CIP-0012.
