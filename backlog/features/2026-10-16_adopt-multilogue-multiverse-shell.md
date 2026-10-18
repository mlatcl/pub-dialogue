---
id: "2026-10-16_adopt-multilogue-multiverse-shell"
title: "Adopt multilogue multiverse shell (variance / enumerate)"
status: "Ready"
priority: "Medium"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: []
owner: "Neil Lawrence"
dependencies: ["2026-10-16_adopt-multilogue-soft-distance"]
tags:
- backlog
- multilogue
- cip0001
---

# Task: Adopt multilogue multiverse shell

## Description

Consumer DO for multilogue CIP-0001 thinning: replace local `variance_decomposition` (and use `enumerate_configurations` / callback runner where the study grid allows). Keep R1–R3 ℓ and artefact loading local.

Upstream: multilogue backlog `2026-10-15_cip0001-thin-pub-dialogue`.

## Acceptance Criteria

- [ ] No duplicated variance-decomposition implementation
- [ ] Paper ℓ callbacks unchanged in behaviour
- [ ] Multiverse tests still pass

## Related

- Multilogue CIP-0001
- Multilogue task: `2026-10-15_cip0001-thin-pub-dialogue`

## Progress Updates

### 2026-10-16

Task created after gap analysis (P0 adoption).
