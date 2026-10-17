---
id: "2026-10-17_cip0017-readme-methodology-note"
title: "CIP-0017: README / methodology note — soft primary, hard late view"
status: "Ready"
priority: "Low"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "documentation"
related_cips: ["0017"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-artefact-migration-canonical-lenses"
tags:
- backlog
- cip0017
- documentation
- methodology
---

# Task: README / methodology note

## Description

Update README (and any short methodology blurb used for the paper) so clustering is described as MPPCA soft topics (k-means initialised), soft sustained through EMD / framing, hard labels only at LLM/report boundaries. Note independent fixed topic vs lens σ². Flag whether published sensitivity tables need re-check under the new default.

## Acceptance Criteria

- [ ] README pipeline bullets no longer imply hard k-means as the sole topic model
- [ ] Soft + EMD role stated accurately (two EMD uses unchanged in spirit)
- [ ] Short note on σ²: fixed per run/config; two floors
- [ ] Optional: one sentence on interim vs end-state if hard artefacts still in flight

## Related

- CIP: 0017

## Progress Updates

### 2026-10-17

Task created (Ready).
