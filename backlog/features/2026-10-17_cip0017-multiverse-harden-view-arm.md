---
id: "2026-10-17_cip0017-multiverse-harden-view-arm"
title: "CIP-0017: multiverse soft default + optional harden-view arm"
status: "Ready"
priority: "Medium"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0017"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-wire-soft-lenses-and-emd"
tags:
- backlog
- cip0017
- multiverse
- sensitivity
---

# Task: Multiverse soft default + harden-view arm

## Description

Update multiverse config so soft topic geometry is the unmarked default. Add an optional arm that uses the hardened (MAP) view for histograms / salience, for sensitivity comparison. Keep lens `sigma2_rule` behaviour; topic \(\sigma^2\) fixed per config (optional later grid — out of scope unless cheap).

## Acceptance Criteria

- [ ] Default multiverse path uses soft histograms / soft topic means
- [ ] Named harden-view arm exists and is documented in `06_multiverse` / metadata sensitivity notes
- [ ] Tests cover config validation for the new dimension
- [ ] No change to “σ² fixed within a cell” rule

## Related

- CIP: 0017

## Progress Updates

### 2026-10-17

Task created (Ready).
