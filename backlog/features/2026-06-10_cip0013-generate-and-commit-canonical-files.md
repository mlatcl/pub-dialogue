---
id: "2026-06-10_cip0013-generate-and-commit-canonical-files"
title: "Run 01a_clustering.ipynb to generate canonical lens mapping files and commit them"
status: "Proposed"
priority: "High"
created: "2026-06-10"
last_updated: "2026-06-10"
category: "features"
related_cips: ["0013"]
owner: ""
dependencies: ["2026-06-10_cip0013-canonical-file-check"]
tags:
- backlog
- framing-lenses
- reproducibility
- cip0013
---

# Task: Generate and commit canonical lens mapping files

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Once the canonical-file check is in place, run `01a_clustering.ipynb` to produce
`outputs/framing_lens_mappings.json` and `outputs/benefit_framing_lens_mappings.json`.
Review the lens names and cluster assignments for coherence, then copy the
reviewed files to their canonical paths and commit them.

This is a one-time human-in-the-loop step. After the canonical files are committed,
subsequent pipeline runs will load them instead of calling the LLM.

## Acceptance Criteria

- [ ] `01a_clustering.ipynb` runs to completion and writes both mapping files to `outputs/`
- [ ] Lens names have been reviewed and are interpretively coherent (no obviously
      misplaced clusters)
- [ ] `pub_dialogue/lens_mapping_canonical_concern.json` committed to git
- [ ] `pub_dialogue/lens_mapping_canonical_benefit.json` committed to git
- [ ] Re-running `01a_clustering.ipynb` cells 36 and 54 with the canonical files
      present produces no LLM call (confirmed via log output or absence of API cost)

## Implementation Notes

Copy step:
```bash
cp outputs/framing_lens_mappings.json pub_dialogue/lens_mapping_canonical_concern.json
cp outputs/benefit_framing_lens_mappings.json pub_dialogue/lens_mapping_canonical_benefit.json
```

Review checklist before committing:
- Are there 7–12 distinct lenses? (too few = over-broad, too many = fragmented)
- Does each lens have at least 2–3 clusters?
- Is there a clearly identifiable "privacy/data" lens?
- Are lens names concise and self-explanatory?

## Related

- CIP: 0013
- PRs:
- Documentation:

## Progress Updates

### 2026-06-10

Task created following acceptance of CIP-0013.
