---
id: "2026-10-17_cip0016-document-local-ci-command"
title: "CIP-0016: document local equivalent of CI pytest"
status: "Completed"
priority: "Medium"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "documentation"
related_cips: ["0016"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0016-add-github-actions-workflow"
tags:
- backlog
- ci
- documentation
- cip0016
---

# Task: Document local CI command

## Description

Add a short note in `README.md` or `SETUP.md` so contributors know CI runs `pytest` after `pip install -e ".[dev]"`, and how to run the same suite locally.

## Acceptance Criteria

- [x] README or SETUP states that PRs run an automated pytest job
- [x] Local commands to install with `dev` and run pytest are listed

## Implementation Notes

Keep it brief — a small subsection is enough. Prefer SETUP if that is where install steps already live; otherwise a short README pointer.

## Related

- CIP: 0016

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0016 acceptance.

### 2026-10-17 (implementation)

Completed on branch cip0016-github-actions-ci.
