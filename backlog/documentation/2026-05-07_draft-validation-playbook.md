---
id: "2026-05-07_draft-validation-playbook"
title: "Draft validation_playbook.md for checking analysis results"
status: "Ready"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "documentation"
related_cips: ["0005"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- validation
- documentation
- playbook
---

# Task: Draft validation_playbook.md for checking analysis results

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Write `validation_playbook.md` at the project root (or in `docs/`). This document provides a step-by-step, repeatable process for validating the dialogue analyser's results using the traceability outputs. It is addressed to a researcher (Jess or Neil) and must be usable without programming knowledge — all steps work with a spreadsheet application and a web browser.

The playbook covers four validation activities defined in CIP-0005:
1. Cluster coherence spot-check (top 10 clusters by size + 5 random)
2. Cross-cutting claim check (verify cross-cutting clusters span ≥3 technologies)
3. Source paragraph verification (random sample of 20 extracted phrases checked against source text)
4. Export pack completeness check (file presence and record count consistency)

## Acceptance Criteria

- [ ] `validation_playbook.md` exists with a clear introduction explaining its purpose and who it is for
- [ ] Activity 1 (cluster coherence) includes step-by-step instructions referencing `cluster_summary.csv`, `cluster_exemplars.json`, and `evidence_pack_paragraphs.html`
- [ ] Activity 2 (cross-cutting check) includes instructions for filtering `traceability_paragraphs.csv` by cluster_id and checking technology distribution
- [ ] Activity 3 (source paragraph verification) includes a random sampling method (e.g. "use column A row numbers and a random number generator") and a comparison checklist
- [ ] Activity 4 (export pack completeness) lists all expected files and the expected record counts with instructions for how to verify them
- [ ] A "suspicious cluster criteria" reference table is included: conditions that should trigger further investigation
- [ ] The playbook references the correct filenames as produced by the current (or post-CIP-0002) output structure
- [ ] All steps are expressed in plain language — no Python code in the main flow (optional code snippets in a separate appendix section are acceptable)

## Implementation Notes

The playbook is a new standalone document. Write it in the form of a numbered checklist that Jess can print or open alongside the HTML outputs. Avoid jargon where possible.

The suspicious cluster criteria table should include at minimum:
| Criterion | Threshold | Action |
|---|---|---|
| Cluster label does not match exemplars | Subjective mismatch | Flag for review |
| Phrases from a single document | > 60% | Flag for review |
| Only one technology represented | < 2 distinct technologies | Flag for review |
| Exemplars contain META_VOCABULARY | Any exemplar uses meta-vocab | Flag for review |
| Very small cluster | < 3 source documents | Flag for review |

This task can proceed in parallel with all CIP-0001/0002/0003 tasks — it does not depend on any code changes.

## Related

- CIP: 0005
- Documentation: [`cip/cip0005.md`](../../cip/cip0005.md)

## Progress Updates

### 2026-05-07
Task created. No code dependencies — can be started immediately in parallel with infrastructure tasks.
