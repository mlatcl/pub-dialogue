---
id: "2026-10-17_cip0016-verify-ci-green-on-pr"
title: "CIP-0016: verify CI check appears and passes on a PR"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "infrastructure"
related_cips: ["0016"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0016-add-github-actions-workflow"
tags:
- backlog
- ci
- verification
- cip0016
---

# Task: Verify CI green on a PR

## Description

Push the workflow on a branch (new PR or update to an open PR such as CIP-0015) and confirm the GitHub Actions check appears and passes. Optionally confirm a deliberate failure goes red.

## Acceptance Criteria

- [ ] A PR shows the new CI check in the GitHub UI
- [ ] The check passes on a known-good commit (install + pytest)
- [ ] Failure mode is visible if/when the suite fails (optional smoke: temporary fail then revert)

## Implementation Notes

If CIP-0015 PR #2 is still open, landing the workflow on that branch or a small follow-up PR both satisfy this task. Fix any install/test failures uncovered by the clean CI environment before marking complete.

## Related

- CIP: 0016

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0016 acceptance.
