---
id: "2026-05-12_cip000c-add-litellm-dependency"
title: "Add litellm to pyproject.toml dependencies"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000C"]
owner: ""
dependencies: []
tags:
- backlog
- cip000c
- litellm
---

# Task: Add litellm to pyproject.toml dependencies

## Description

Add `litellm>=1.40` to the core dependencies in `pyproject.toml`.  `openai`
stays as a dependency (needed for embeddings fallback and type stubs).
`anthropic` and `google-generativeai` are NOT added — litellm handles
provider routing without requiring them as hard dependencies.

## Acceptance Criteria

- [ ] `litellm>=1.40` present in `[project] dependencies` in `pyproject.toml`
- [ ] `openai>=1.10` remains in dependencies
- [ ] `pip install -e ".[dev]"` completes without error

## Implementation Notes

Add the line immediately after `openai` in the dependencies list to keep
provider-related deps grouped.

## Related

- CIP: 000C

## Progress Updates

### 2026-05-12

Task created.
