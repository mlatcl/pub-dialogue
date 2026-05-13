---
id: "2026-05-12_cip000c-update-readme"
title: "Update README.md with supported LLM providers table"
status: "Completed"
priority: "Medium"
created: "2026-05-12"
last_updated: "2026-05-13"
category: "documentation"
related_cips: ["000C"]
owner: ""
dependencies: ["2026-05-12_cip000c-update-notebooks"]
tags:
- backlog
- cip000c
- documentation
---

# Task: Update README.md with supported LLM providers table

## Description

Add a "Supported LLM providers" section to `README.md` listing the tested
providers, the model string format, and the env-var required for each.

## Acceptance Criteria

- [ ] README has a "Supported LLM providers" section (or subsection under "Running locally")
- [ ] Table includes at minimum: OpenAI, Anthropic, Google Gemini
- [ ] Each row shows: provider, example `LLM_MODEL` string, required env-var
- [ ] Note that `EMBEDDING_MODEL` change requires full re-run of `01_processing.ipynb`
- [ ] Link to litellm provider docs for the full list

## Implementation Notes

Example table:

| Provider | Example `LLM_MODEL` | Required env-var |
|---|---|---|
| OpenAI (default) | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini/gemini-2.0-flash` | `GOOGLE_API_KEY` |

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
