---
id: "2026-10-17_cip0017-addressstage-soft-throughout"
title: "CIP-0017: AddressStage / 01a soft-throughout topic fit"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0017"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-mppca-fit-primitive"
- "2026-10-17_cip0017-harden-view-helpers"
tags:
- backlog
- cip0017
- address
- soft
- mppca
---

# Task: AddressStage / 01a soft-throughout

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Retarget `AddressStage.cluster` (and `01a_clustering.ipynb`) so primary topic geometry is multilogue MPPCA soft responsibilities + component means. Checkpoint soft state. Call harden-view helpers only in labelling / lens-partition cells. Drop sklearn `cluster_centers_` as the stored topic definition.

Depends on multilogue tasks `2026-10-17_cip0017-mppca-fit-primitive` and `2026-10-17_cip0017-harden-view-helpers`.

## Acceptance Criteria

- [ ] Cluster path returns / checkpoints responsibilities and \(\mu\); hard labels optional derived
- [ ] `01a` label and lens cells use harden-view at the boundary only
- [ ] Module docs state soft primary
- [ ] Tests updated for soft checkpoints (no dependence on deleted hard-only contract)

## Implementation Notes

Thin onto multilogue; do not re-implement MPPCA in `address.py`. Topic \(\sigma^2\) fixed per config (CIP-0017 decision).

## Related

- CIP: 0017
- Multilogue: `2026-10-17_cip0017-mppca-fit-primitive`, `2026-10-17_cip0017-harden-view-helpers`

## Progress Updates

### 2026-10-17

Task created (Ready) on CIP-0017 Accept.
