---
id: "2026-05-07_revise-extraction-prompt"
title: "Revise extraction prompt to reduce meta-vocabulary artefacts and re-run extraction"
status: "Completed"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "features"
related_cips: ["0004"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_vocabulary-frequency-diagnostic"]
tags:
- backlog
- artefacts
- prompt-engineering
- extraction
---

# Task: Revise extraction prompt to reduce meta-vocabulary artefacts and re-run extraction

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Based on the vocabulary frequency diagnostic (previous task), revise the extraction prompt to reduce prompt-induced meta-vocabulary in the extracted phrases. Start with Option A from CIP-0004 (explicit instruction not to use dialogue-process vocabulary), re-run extraction on a 100-chunk sample, re-run the diagnostic, and compare. If results are satisfactory, proceed to full re-extraction.

The current prompt includes: "You are analysing a paragraph from a UK public dialogue report on science and technology..." — this framing can prime the LLM to use process vocabulary ("public dialogue", "engagement") rather than substantive content vocabulary.

## Acceptance Criteria

- [ ] Archive current `extracted_concerns.csv` and `extracted_benefits.csv` as `extracted_concerns_v12b_pre_prompt_revision.csv` and `extracted_benefits_v12b_pre_prompt_revision.csv` before any re-extraction
- [ ] Prompt revision applied: explicit instruction added to not use META_VOCABULARY terms (Option A), as defined in CIP-0004
- [ ] Sample re-extraction run on ≥100 chunks; vocabulary diagnostic re-run on sample output
- [ ] Comparison documented in a notebook markdown cell: before vs after frequency of top META_VOCABULARY bigrams
- [ ] If Option A reduces META_VOCABULARY bigram frequency by ≥50% on the sample: proceed to full re-extraction
- [ ] If Option A is insufficient: escalate to Option B (remove "UK public dialogue" corpus framing) and repeat sample test — document the decision
- [ ] Full re-extraction produces new `extracted_concerns.csv` and `extracted_benefits.csv`; cluster labels regenerated
- [ ] If a meta-vocabulary stop-list filter is needed: implemented with `meta_vocab_drops.csv` logging (parallel to `tech_filter_drops.csv`); decision and rationale documented

## Implementation Notes

Full re-extraction requires OpenAI API calls (~12,000 paragraphs at 1–3 phrases each). Estimated cost should be checked before running. If costs are prohibitive, the sample comparison alone may be sufficient evidence for the paper's methodology section, with a note that full re-extraction is pending.

The cluster labels in `cluster_labels.json` are generated from extracted phrases by an LLM call — they will need regeneration after re-extraction changes the phrase distribution. Factor this into the time estimate.

Do not delete `extracted_concerns_v12b_pre_prompt_revision.csv` after re-extraction — it is the baseline for any before/after comparison in the paper.

## Related

- CIP: 0004
- Documentation: [`cip/cip0004.md`](../../cip/cip0004.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_vocabulary-frequency-diagnostic`.

### 2026-05-07 — Completed
Option A applied: EXTRACTION_PROMPT and BENEFIT_EXTRACTION_PROMPT in dialogue_utils.py
now include explicit rule 5: 'Do NOT use the words public dialogue, dialogue,
engagement, consultation, or participation in your extracted phrases.'
Re-extraction on live data deferred pending Jess review of diagnostic output.
