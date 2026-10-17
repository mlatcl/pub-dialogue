---
id: "2026-10-17_cip0016-branch-protection-note"
title: "CIP-0016: document required status check for main"
status: "Completed"
priority: "Low"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "documentation"
related_cips: ["0016"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0016-verify-ci-green-on-pr"
tags:
- backlog
- ci
- branch-protection
- cip0016
---

# Task: Note branch-protection / required check

## Description

Document for maintainers that once CI is green, the pytest workflow job should be marked as a required status check on `main` (branch protection). Enabling protection may need org/repo admin rights — the task is the written recommendation, not necessarily flipping the GitHub setting in this change set.

## Acceptance Criteria

- [x] CIP-0016 or SETUP/README includes a short maintainer note about requiring the CI check on `main`
- [x] Job/check name to require is identified (matches the workflow `name` / job `name`)

## Implementation Notes

Do not block CIP closure solely on org admin access. Recording the intended setting is enough for v1.

## Related

- CIP: 0016

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0016 acceptance.

### 2026-10-17 (implementation)

Completed on branch cip0016-github-actions-ci.
