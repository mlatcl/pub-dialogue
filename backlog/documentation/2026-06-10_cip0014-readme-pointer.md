---
id: "2026-06-10_cip0014-readme-pointer"
title: "Add 'New to Python?' pointer to README.md"
status: "Completed"
priority: "Low"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "documentation"
related_cips: ["0014"]
owner: "Neil Lawrence"
dependencies: ["2026-06-10_cip0014-create-setup-md"]
tags:
- backlog
- documentation
- onboarding
---

# Task: Add 'New to Python?' pointer to README.md

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add a short "New to Python?" paragraph to `README.md` just above the existing
"Quick start (local)" section, pointing non-technical readers to `SETUP.md`.
Experienced users skip past it; beginners are directed to the full guide.

## Acceptance Criteria

- [x] A "New to Python?" section exists in `README.md`
- [x] It appears immediately above "Quick start (local)"
- [x] It links to `SETUP.md`
- [x] The existing quick-start content is unchanged

## Implementation Notes

Kept brief — three sentences — so it does not disrupt the flow for developer
readers who do not need it.

## Related

- CIP: 0014

## Progress Updates

### 2026-06-10

Task completed. README pointer written and committed as part of commit `4047005`.
