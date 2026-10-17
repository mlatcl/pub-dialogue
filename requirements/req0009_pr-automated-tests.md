---
id: "0009"
title: "Pull requests are gated on an automated test suite"
status: "In Progress"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
related_tenets: ["access-assess-address"]
stakeholders: ["Neil Lawrence"]
tags: ["ci", "testing", "pull-requests", "reproducibility"]
---

# REQ-0009: Pull requests are gated on an automated test suite

## Description

Changes proposed via pull request must be checked automatically before merge. Opening or updating a PR must run the project’s installable test suite in a clean environment, and a failing suite must block (or clearly fail) the PR check so regressions are not merged unnoticed.

The outcome is visibility and a gate — not that every analysis notebook is executed in CI, and not that the full PDF corpus is required on every push.

**Why this matters**: Local pytest is easy to skip. CIP-0015 showed that PRs can land with no checks at all when CI is absent. Automated gating makes access/assess/address package changes safer for collaborators and for follow-on work that depends on lynguine and other git dependencies.

**Who benefits**: Maintainers reviewing PRs; collaborators who need confidence that `main` installs and tests pass; anyone changing `pub_dialogue` without re-running the full analysis pipeline.

## Acceptance Criteria

- [ ] Every pull request against the default branch triggers an automated check that installs the package (including declared dependencies) and runs the project test suite
- [ ] A failing test suite causes the check to fail in a way visible on the PR
- [ ] The check does not require the local PDF corpus or paid API keys
- [ ] Contributors can see how to run the same suite locally (documented briefly, e.g. in README or SETUP)

## Notes

Which CI host (GitHub Actions, etc.), matrix of Python versions, and whether checks are required branch-protection rules are design choices for the implementing CIP. Expanding coverage of the suite is valuable but separate from establishing the gate.

## References

- **Related Tenets**: [access-assess-address](../tenets/pub-dialogue/access-assess-address.md)
- **Related CIP**: [CIP-0016](../cip/cip0016.md) (proposed)

## Progress Updates

### 2026-10-17
Requirement created after CIP-0015 PR showed no CI workflows. Status Ready so a CIP can implement the gate.

### 2026-10-17 (later)
CIP-0016 accepted; backlog tasks created. Status → In Progress.
