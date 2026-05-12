---
id: "2026-05-12_cip000c-update-tests"
title: "Update test mocks to use LLMClient spec; add TestLLMClient"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000C"]
owner: ""
dependencies: ["2026-05-12_cip000c-update-utils"]
tags:
- backlog
- cip000c
- testing
---

# Task: Update test mocks to use LLMClient spec; add TestLLMClient

## Description

Replace the existing `MagicMock` openai-based client constructions in
`tests/test_dialogue_utils.py` with `MagicMock(spec=LLMClient)`.  Add a
new `TestLLMClient` class that tests the wrapper itself (using mocked
litellm at module level).

## Acceptance Criteria

- [ ] All existing `MagicMock()` client mocks replaced with `MagicMock(spec=LLMClient)`
- [ ] Mock `.complete.return_value` set to a JSON string (for extraction tests)
- [ ] Mock `.embed.return_value` set to `[[0.1, 0.2, ...]]` (for embedding tests)
- [ ] `TestLLMClient` class added with at least:
  - `test_complete_calls_litellm` — patches `litellm.completion`, verifies return is a string
  - `test_embed_calls_litellm` — patches `litellm.embedding`, verifies return shape
  - `test_provider_routing` — parametrised over `gpt-4o-mini`, `claude-3-5-haiku-latest`, `gemini/gemini-2.0-flash` model strings (all mocked)
- [ ] Full test suite passes (171+ tests)

## Implementation Notes

Mock litellm inside `TestLLMClient` only — not in any other test class.
Other tests just use `MagicMock(spec=LLMClient)` and never touch litellm.

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
