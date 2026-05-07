---
id: "2026-05-07_vocabulary-frequency-diagnostic"
title: "Add vocabulary frequency diagnostic and inspect current outputs for meta-vocabulary"
status: "Ready"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "features"
related_cips: ["0004"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_write-extraction-yield-diagnostics"]
tags:
- backlog
- artefacts
- vocabulary
- diagnostic
- prompt
---

# Task: Add vocabulary frequency diagnostic and inspect current outputs for meta-vocabulary

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Before changing the extraction prompt, measure the current state of the "public dialogue" artefact. Add a post-extraction diagnostic cell that computes unigram and bigram frequencies across all extracted phrases, writes the results to CSV, and flags any terms from a curated `META_VOCABULARY` list.

Also inspect the `tech_filter_drops.csv` from the previous task to check whether prompt-induced phrases are already being partially suppressed by the tech-word filter.

This task is diagnostic only — it does not change the prompt or the filter. The findings inform the next task (`2026-05-07_revise-extraction-prompt`).

## Acceptance Criteria

- [ ] A `META_VOCABULARY` constant is defined in `dialogue_utils.py` containing at minimum: `["public dialogue", "dialogue participants", "public engagement", "engagement process", "dialogue process", "public consultation", "stakeholder engagement"]`
- [ ] A post-extraction notebook cell computes unigram and bigram token frequencies over all phrases in `extracted_concerns.csv` and `extracted_benefits.csv`
- [ ] `outputs/concern_vocab_frequency.csv` is written with columns: `token`, `frequency`, `pct_of_phrases`, `is_meta_vocab`
- [ ] `outputs/benefit_vocab_frequency.csv` is written with the same schema
- [ ] The top-100 tokens are printed to the notebook cell output, with META_VOCABULARY terms highlighted
- [ ] A written summary (comment in the notebook cell or a separate markdown cell) documents: which META_VOCABULARY terms appear in the top-50 bigrams, their frequency percentage, and whether they also appear in `tech_filter_drops.csv`
- [ ] The summary conclusion states whether the artefact is confirmed as significant (e.g. any META_VOCABULARY bigram appearing in >5% of phrases is flagged as significant)

## Implementation Notes

Token frequency should be computed over the extracted phrase text, not over source paragraphs. Bigrams are formed from consecutive word pairs within a single phrase (not across phrase boundaries).

Short stop-words (a, the, of, in, to, etc.) should be excluded from the frequency count, but META_VOCABULARY terms should be checked regardless of whether their component words are stop-words.

The goal is a simple, readable output — a CSV and a printed table are sufficient. No visualisation is required for this diagnostic task (though a bar chart would be a nice addition if time permits).

## Related

- CIP: 0004
- Documentation: [`cip/cip0004.md`](../../cip/cip0004.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_write-extraction-yield-diagnostics` (needs tech_filter_drops.csv). Can also be run against existing extracted_concerns/benefits.csv without re-running extraction.
