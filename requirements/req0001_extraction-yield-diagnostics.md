---
id: "0001"
title: "Extraction pipeline reports distinguishable yield statistics"
status: "Proposed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
related_tenets: []
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["extraction", "diagnostics", "concerns", "benefits"]
---

# REQ-0001: Extraction pipeline reports distinguishable yield statistics

## Description

The dialogue analyser pipeline extracts concern and benefit phrases from paragraph chunks using an LLM. Currently, the pipeline reports the total number of phrases extracted but does not distinguish between three distinct reasons why a paragraph may yield no phrases:

1. **Design-intent empties** — the paragraph is boilerplate, process description, or dialogue administration prose that correctly produces `NO_CONCERN` / `NO_BENEFIT` from the LLM
2. **Tech-filter drops** — the LLM did produce a phrase, but it was discarded because it contained a substring from `tech_words` (e.g. a phrase containing `"ai"` mid-word)
3. **Silent errors** — an API exception was caught silently and the paragraph returned an empty list due to a failure rather than genuine absence of content

Without this breakdown, it is impossible to tell whether a high rate of empty extractions reflects a conservative but correct design decision, an over-aggressive filter, or unreported API failures.

**Why this matters**: Distinguishing these three categories is essential for trusting the analysis results and for any downstream decisions about prompt or filter tuning. It connects to the principle that research pipelines should be transparent and auditable.

**Who benefits**: Researchers using the output (Neil, Jess, paper co-authors); reviewers assessing the methodology.

## Acceptance Criteria

- [ ] After each extraction run, a summary table is written to disk (e.g. `extraction_yield_summary.csv`) with counts and percentages for: total chunks processed, design-intent empties (LLM returned sentinel), tech-filter drops (phrase existed but was removed), silent errors (exception caught), and net phrases retained
- [ ] The summary is also printed to the notebook cell output at extraction completion
- [ ] Silent errors are no longer silently swallowed; they are counted and optionally logged to a separate file (`extraction_errors.log`) with the chunk ID and exception message
- [ ] The tech-word filter logs each dropped phrase and the matching substring to a separate file (`tech_filter_drops.csv`) so the aggressiveness of the filter can be assessed

## Notes

The current tech-word filter uses substring matching, which means a word like `"tailoring"` would be dropped because it contains `"ai"`. Whether this is intentional or not should be documented. REQ-0001 does not mandate changing the filter logic — only making its behaviour visible.

## References

- **Related Tenets**: (none defined yet for this project)
- **External Links**: See `public_dialogue_analyser_v12b_4.ipynb` cells covering `extract_concerns_from_paragraph` and `extract_benefits_from_paragraph`

## Progress Updates

### 2026-05-07
Requirement proposed based on Jess's observation that many paragraphs yield no concerns or benefits, and on notebook analysis revealing three distinct root causes that are currently conflated.
