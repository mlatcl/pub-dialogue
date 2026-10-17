---
id: "2026-10-17_cip0017-artefact-migration-canonical-lenses"
title: "CIP-0017: artefact migration and canonical lens map update"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0017", "0013"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-wire-soft-lenses-and-emd"
tags:
- backlog
- cip0017
- artefacts
- lenses
- migration
---

# Task: Artefact migration and canonical lenses

## Description

Decide which checkpoints regenerate under soft-throughout (responsibilities, \(\mu\), mixture weights, soft memberships). Run migration for the working corpus as needed. If component ids shift, update canonical framing-lens mappings under the REQ-0007 / CIP-0013 deliberate-edit process (committed files, not accidental LLM regen).

## Acceptance Criteria

- [ ] Written note: which artefacts regen now vs later
- [ ] Soft checkpoints loadable by AccessStage / 01a reload path
- [ ] Canonical lens maps either validated against new component ids or deliberately rewritten and committed
- [ ] No silent overwrite of canonical lens JSON from a stochastic LLM call

## Implementation Notes

Coordinate with any open CIP-0013 work. Interim hard centroids may remain until regen completes.

## Related

- CIP: 0017, 0013
- REQ-0007 (via CIP-0013 process)

## Progress Updates

### 2026-10-17

Task created (Ready).
