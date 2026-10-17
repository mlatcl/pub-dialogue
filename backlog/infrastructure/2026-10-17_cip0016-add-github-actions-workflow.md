---
id: "2026-10-17_cip0016-add-github-actions-workflow"
title: "CIP-0016: add GitHub Actions workflow for pytest"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "infrastructure"
related_cips: ["0016"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- ci
- github-actions
- pytest
- cip0016
---

# Task: Add GitHub Actions CI workflow

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add `.github/workflows/ci.yml` that runs on pull requests to `main` and pushes to `main`. Steps: checkout, setup Python 3.11, `pip install -e ".[dev]"`, `pytest`. No PDF corpus, no API secrets. Must successfully install git dependencies declared in `pyproject.toml` (e.g. `lynguine[documents]`).

## Acceptance Criteria

- [ ] Workflow file exists under `.github/workflows/`
- [ ] Triggers cover `pull_request` and `push` to `main`
- [ ] Job installs the package with the `dev` extra and runs pytest
- [ ] Job does not require corpus PDFs or OpenAI credentials

## Implementation Notes

Keep a single Python version for v1. Use `actions/checkout` and `actions/setup-python` current majors. Hatch already has `allow-direct-references` for git deps after CIP-0015.

## Related

- CIP: 0016

## Progress Updates

### 2026-10-17

Task created (Ready) after CIP-0016 acceptance.
