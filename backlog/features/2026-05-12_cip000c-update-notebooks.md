---
id: "2026-05-12_cip000c-update-notebooks"
title: "Update 01_processing.ipynb and 01a_clustering.ipynb for LLMClient"
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
- notebooks
---

# Task: Update 01_processing.ipynb and 01a_clustering.ipynb for LLMClient

## Description

Update the config and API access cells in `01_processing.ipynb` (and
`01a_clustering.ipynb` if it constructs its own client) to use `LLMClient`.

Config cell changes:
- Drop `LLM_PROVIDER`
- Keep `LLM_MODEL` and `EMBEDDING_MODEL`

API access cell changes (see CIP-000C for full cell source):
- Import `LLMClient` from `pub_dialogue.client`
- Infer which env-var to prompt for from the model name prefix
- Construct `client = LLMClient(model=LLM_MODEL, embedding_model=EMBEDDING_MODEL)`
- Remove `OpenAI(api_key=...)` construction and `client.models.list()` check

## Acceptance Criteria

- [ ] `LLM_PROVIDER` variable removed from config cells
- [ ] `EMBEDDING_MODEL` variable present in config cells
- [ ] API access cell constructs `LLMClient` not `OpenAI`
- [ ] Provider key inference works for openai / anthropic / google model prefixes
- [ ] Notebook runs top-to-bottom without NameError

## Implementation Notes

The API access cell in CIP-000C Detailed Description has the full
replacement source.  Apply it verbatim, adjusting only cell IDs.

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
