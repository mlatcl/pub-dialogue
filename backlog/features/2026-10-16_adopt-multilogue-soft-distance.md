---
id: "2026-10-16_adopt-multilogue-soft-distance"
title: "Adopt multilogue.soft / multilogue.distance (CIP-0005)"
status: "Completed"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: []
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- multilogue
- cip0005
---

# Task: Adopt multilogue.soft / multilogue.distance

## Description

Consumer DO for multilogue CIP-0005: depend on `multilogue[distance]`, keep `pub_dialogue.distance` and soft helpers as thin wrappers, land branch `cip0005-depend-multilogue`.

Upstream tracking: multilogue backlog `2026-10-16_cip0005-finish-pub-soft-distance-adopt`.

## Acceptance Criteria

- [ ] Dependency declared; hatch allows direct references
- [ ] Soft PPCA + document EMD delegated; tests green
- [ ] PR/merge of `cip0005-depend-multilogue`

## Related

- Multilogue CIP-0005
- Multilogue task: `2026-10-16_cip0005-finish-pub-soft-distance-adopt`

## Progress Updates

### 2026-10-16

Thin-out implemented on branch; parity vs main confirmed.
