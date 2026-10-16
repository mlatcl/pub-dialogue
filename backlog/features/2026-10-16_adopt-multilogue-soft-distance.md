---
id: "2026-10-16_adopt-multilogue-soft-distance"
title: "Adopt multilogue.soft / multilogue.distance (CIP-0005)"
status: "In Progress"
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

- [x] Dependency declared; hatch allows direct references
- [x] Soft PPCA + document EMD delegated; tests green
- [x] Multilogue-native recreation notebook confirms gap decisions + soft AI−nonAI ranks
- [ ] PR/merge of `cip0005-depend-multilogue` (deferred until recreation gate is accepted)

## Related

- Multilogue CIP-0005
- Multilogue task: `2026-10-16_cip0005-finish-pub-soft-distance-adopt`

## Progress Updates

### 2026-10-16

Thin-out implemented on branch; unit parity vs main confirmed. Adopt PR opened then judged premature — added `notebooks/multilogue_native_soft_distance.ipynb` (21/21 checks: CIP-0005–0007 APIs, soft gap Spearman 0.976 vs saved table, neighbour rules, distance smoke, keep-local legacy/ℓ).
