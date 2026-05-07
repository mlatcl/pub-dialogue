---
id: "0005"
title: "There is a defined, repeatable process for validating analysis results"
status: "Proposed"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
related_tenets: []
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["validation", "results", "traceability", "quality-assurance"]
---

# REQ-0005: There is a defined, repeatable process for validating analysis results

## Description

The dialogue analyser pipeline produces traceability outputs (`traceability_paragraphs.csv`, `evidence_pack_paragraphs.html`, `cluster_exemplars.json`) that link clusters back to source paragraphs. However, there is currently no documented process for using these outputs to systematically check whether:

- Clusters are semantically coherent (the exemplars actually represent the cluster label)
- Cluster assignments are correct for individual phrases
- Suspicious clusters (e.g. those dominated by a single technology or a single document) are identified and investigated
- The extracted phrases in the export pack match what is expected

Without such a process, the analysis is difficult to quality-assure before publication, and it is unclear which checks Jess and Neil should be doing when they "go through results in depth".

**Why this matters**: A validation process transforms the pipeline from a black box into an auditable research instrument. It also provides a shared protocol that Jess and Neil can use together, and documents the basis for claims made in the resulting paper.

**Who benefits**: Neil, Jess, paper co-authors, and reviewers.

## Acceptance Criteria

- [ ] A validation playbook (checklist or guide) exists that describes step-by-step how to use `traceability_paragraphs.csv`, `cluster_exemplars.json`, and `evidence_pack_paragraphs.html` to spot-check results
- [ ] The playbook includes a sampling strategy (e.g. review the top 10 clusters by size, plus 5 random clusters)
- [ ] The playbook includes criteria for flagging a cluster as suspicious (e.g. >50% of phrases from a single document, cluster label does not match exemplars, cluster contains phrases from only one technology)
- [ ] The playbook includes a process for checking extracted paragraphs in the export pack against source PDF content
- [ ] The playbook is usable by a researcher without programming knowledge (i.e. it works with spreadsheet tools or the HTML outputs, not only via Python)

## Notes

The playbook could take several forms: a standalone markdown document, a section of the notebook, or a separate validation notebook. The choice belongs in the corresponding CIP. The key requirement is that the process exists, is documented, and is repeatable.

## References

- **Related Tenets**: (none defined yet for this project)
- **External Links**: See `outputs/traceability_paragraphs.csv`, `outputs/evidence_pack_paragraphs.html`, `outputs/cluster_exemplars.json`; Jess's question about "how to go through results in depth" and "what checking to do against exported paragraphs in the export pack"

## Progress Updates

### 2026-05-07
Requirement proposed based on Jess's questions about how to validate results and check the export pack against source content.
