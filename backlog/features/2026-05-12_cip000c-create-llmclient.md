---
id: "2026-05-12_cip000c-create-llmclient"
title: "Create pub_dialogue/client.py with LLMClient wrapper"
status: "Completed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-13"
category: "features"
related_cips: ["000C"]
owner: ""
dependencies: ["2026-05-12_cip000c-add-litellm-dependency"]
tags:
- backlog
- cip000c
- litellm
---

# Task: Create pub_dialogue/client.py with LLMClient wrapper

## Description

Create `pub_dialogue/client.py` containing the `LLMClient` class — a thin
dependency-injection wrapper around litellm.  litellm is imported lazily
inside each method (not at module level) so analysis notebooks that never
call the API don't pay the import cost.

Export `LLMClient` from `pub_dialogue/__init__.py`.

## Acceptance Criteria

- [ ] `pub_dialogue/client.py` exists with `LLMClient` class
- [ ] `LLMClient.__init__` accepts `model` and `embedding_model` kwargs
- [ ] `LLMClient.complete(messages, **kwargs)` calls `litellm.completion` and returns a string
- [ ] `LLMClient.embed(texts)` calls `litellm.embedding` and returns `list[list[float]]`
- [ ] Both methods import litellm lazily (inside the method body)
- [ ] `from pub_dialogue import LLMClient` works
- [ ] Docstrings present on class and both methods

## Implementation Notes

See CIP-000C Detailed Description for the full class definition.  The lazy
import pattern (`import litellm` inside the method) is intentional — do not
move it to the top of the file.

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
