---
id: "2026-10-17_cip0017-wire-soft-lenses-and-emd"
title: "CIP-0017: wire soft lenses + document EMD to soft topic geometry"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0017"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-addressstage-soft-throughout"
- "2026-10-17_cip0017-soft-document-histograms"
tags:
- backlog
- cip0017
- soft
- emd
- lenses
---

# Task: Wire soft lenses and document EMD

## Description

Point soft-lens mixture weights and document-distance analysis at MPPCA \(\mu\) / soft document histograms. Thin `pub_dialogue.address` / `distance` / notebooks (02–03, 06–07 as needed) onto `multilogue.soft` and `multilogue.distance`. Lens σ²\* remains shared and fixed after selection (existing rule + multilogue flat-EMD harden when available).

## Acceptance Criteria

- [ ] Soft lens path consumes component means from soft topic fit (no sklearn centres)
- [ ] Document EMD default uses soft histograms
- [ ] Framing profiles that used `mixture_weights[cluster_id]` have a defined soft path (via harden view or soft composition — document choice)
- [ ] Pub does not fork PPCA/EMD maths locally

## Implementation Notes

Prefer phrase→lens salience via harden-then-lookup only where notebooks still need cluster ids; longer-term soft composition can be a follow-on if needed.

## Related

- CIP: 0017
- Multilogue: `2026-10-17_cip0017-soft-document-histograms`

## Progress Updates

### 2026-10-17

Task created (Ready).
