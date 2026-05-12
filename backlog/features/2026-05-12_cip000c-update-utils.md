---
id: "2026-05-12_cip000c-update-utils"
title: "Update pub_dialogue/utils.py to use LLMClient"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000C"]
owner: ""
dependencies: ["2026-05-12_cip000c-create-llmclient"]
tags:
- backlog
- cip000c
- litellm
---

# Task: Update pub_dialogue/utils.py to use LLMClient

## Description

Replace direct `openai.OpenAI` client calls in `pub_dialogue/utils.py` with
calls to `LLMClient.complete()` and `LLMClient.embed()`.  The `model`
parameter is removed from function signatures (it now lives on the client
instance).  The `client` positional argument is retained but its type
annotation changes from `openai.OpenAI` to `LLMClient`.

Functions affected:
- `extract_phrases(chunk_text, kind, client)`
- `label_cluster(phrases, client)`
- `embed_texts(texts, client)`

## Acceptance Criteria

- [ ] `from openai import OpenAI` removed from `utils.py`
- [ ] `extract_phrases` calls `client.complete(messages)` not `client.chat.completions.create(...)`
- [ ] `label_cluster` calls `client.complete(messages)` not `client.chat.completions.create(...)`
- [ ] `embed_texts` calls `client.embed(texts)` not `client.embeddings.create(...)`
- [ ] `model` parameter removed from all three function signatures
- [ ] Type annotations updated to `client: LLMClient`
- [ ] All existing tests still pass (after test mocks updated in next task)

## Implementation Notes

The `model` removal is a breaking change for callers that pass `model=`
explicitly.  Notebooks will be updated in a separate task.

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
