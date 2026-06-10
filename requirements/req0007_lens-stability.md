---
id: "0007"
title: "Framing lens assignments are stable across pipeline runs and their variability is characterised"
status: "Ready"
priority: "High"
created: "2026-06-10"
last_updated: "2026-06-10"
related_tenets: []
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["reproducibility", "framing-lenses", "sensitivity", "clustering", "pipeline"]
---

# REQ-0007: Framing lens assignments are stable across pipeline runs and their variability is characterised

## Description

The pipeline groups concern and benefit clusters into higher-level "framing lenses" by calling an LLM. Because this call has no fixed schema or seed, each run produces different lens names and potentially different cluster-to-lens assignments. Comparing two pipeline runs revealed that the direction of AI over/under-indexing on a "privacy/data" lens reversed between runs — threatening the paper's central claim about AI distinctiveness.

In parallel, the k-means clustering step that produces the clusters has no fixed random seed, so cluster IDs and assignments also vary between runs. Together, these two stochastic steps mean that the AI distinctiveness figures in the paper cannot currently be reproduced by re-running the notebook.

The requirement is that lens assignments are treated as a committed research design decision rather than a stochastic pipeline output, and that the sensitivity of lens-level AI distinctiveness findings to different plausible lens groupings is measured and reported.

**Why this matters**: If the direction of the key finding (AI is distinctively focused on data/privacy concerns) changes depending on how the LLM chose to group clusters on a given run, the finding is not robust. Reviewers and readers need to know whether the finding holds under alternative reasonable lens groupings. Reproducibility is also a prerequisite for the paper's methodology being auditable.

**Who benefits**: Neil, Jess, paper co-authors, peer reviewers, and any researcher attempting to reproduce or extend the analysis.

## Acceptance Criteria

- [ ] Re-running the full pipeline on the same corpus produces identical cluster IDs and assignments (k-means seed is fixed)
- [ ] Re-running the full pipeline on the same corpus produces identical lens names and cluster-to-lens assignments (canonical mapping loaded from a committed file rather than regenerated from LLM)
- [ ] The canonical lens mapping files are committed to the repository and can be updated only by a deliberate research decision (not as a side-effect of re-running)
- [ ] The robustness notebook includes a lens-scheme sensitivity section that runs the LLM lens-grouping step N ≥ 3 times and reports whether the direction of AI over-indexing on privacy/data-type clusters is consistent across runs
- [ ] The lens-scheme sensitivity result is reported in the paper alongside the existing k-sensitivity and prompt-sensitivity results

## Notes

This requirement does not mandate specific file names or implementation choices — those belong in the corresponding CIP. The key outcome is that lens assignments are stable and their variability is bounded and documented.

The requirement extends the existing sensitivity framework (REQ-0002: sensitivity outputs distinct; REQ-0005: validation process) to cover the framing-lens grouping stage, which was previously untested.

## References

- **Related requirements**: REQ-0002 (sensitivity outputs non-overwriting), REQ-0005 (validation process)
- **Related CIPs**: CIP-0012 (prompts externalised to YAML — establishes the pattern of treating LLM outputs as committed design decisions)
- **Evidence**: Comparison of `outputs/ai_vs_nonai_lens_doc_weighted.csv` (current run) vs `2026-05-dialogue-results-sketch.md` (earlier run) shows AI privacy distinctiveness reversed direction (+16.7pp vs −4.5pp)

## Progress Updates

### 2026-06-10
Requirement proposed following analysis of discrepancy between two pipeline runs that produced different lens assignments and opposite AI-distinctiveness directions for privacy-type clusters.
