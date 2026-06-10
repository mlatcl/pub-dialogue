---
id: "2026-06-10_cip0014-create-setup-md"
title: "Create SETUP.md beginner setup guide"
status: "Completed"
priority: "Medium"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "documentation"
related_cips: ["0014"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- documentation
- onboarding
---

# Task: Create SETUP.md beginner setup guide

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Write a step-by-step local setup guide at the repository root (`SETUP.md`)
for non-technical collaborators who have never used Python, the terminal, or
git before. macOS is the primary platform; Windows stubs are included for
future completion.

## Acceptance Criteria

- [x] `SETUP.md` exists at the repository root
- [x] Covers: open terminal, install Python, install git, clone repo, create
      venv, activate venv, install packages, configure `.env`, launch Jupyter
- [x] Each step ends with a verifiable outcome
- [x] macOS instructions are the primary path; Windows shown as stubs
- [x] Troubleshooting table covers common failure modes

## Implementation Notes

Terminal-first structure: Step 1 opens the terminal so all subsequent commands
are run from the same environment. Python.org installer used (not Anaconda) to
stay consistent with the project's pip-based toolchain. ZIP download route
removed in favour of `git clone` to avoid leaving collaborators on a dead-end
copy with no update path.

## Related

- CIP: 0014

## Progress Updates

### 2026-06-10

Task completed. `SETUP.md` written and committed as part of commit `4047005`.
