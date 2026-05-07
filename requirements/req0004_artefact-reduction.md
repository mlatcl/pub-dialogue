---
id: "0004"
title: "Extracted phrases reflect paragraph content not prompt framing"
status: "Proposed"
priority: "Medium"
created: "2026-05-07"
last_updated: "2026-05-07"
related_tenets: []
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["prompt-engineering", "artefacts", "extraction", "validation"]
---

# REQ-0004: Extracted phrases reflect paragraph content not prompt framing

## Description

The extraction prompt currently tells the LLM that the paragraph is from a "UK public dialogue report". This corpus framing can prime the model to generate concern and benefit phrases that use vocabulary from the prompt itself — words like "public dialogue", "dialogue participants", and "engagement" — rather than vocabulary that reflects the substantive content of the paragraph.

Because these words are not in the `tech_words` stop-list, they pass through the filter and can appear with high frequency across clusters, making them look like genuine cross-cutting themes when they may simply be artefacts of the prompt wording. Jess observed: "the fact that public dialogue comes up so much in concerns and benefits makes me think it is just people talking about public dialogue."

The requirement is that the pipeline should produce extracted phrases whose vocabulary is driven by paragraph content rather than by meta-vocabulary introduced through prompt framing, and that any systematic over-representation of prompt-derived vocabulary should be detectable.

**Why this matters**: Artefacts that cannot be distinguished from genuine findings undermine the validity of the analysis. A paper based on results that include prompt-primed vocabulary would overstate the frequency of "public dialogue" as a substantive concern or benefit.

**Who benefits**: Neil, Jess, paper reviewers, and the broader research community assessing the methodology.

## Acceptance Criteria

- [ ] A vocabulary frequency diagnostic is produced after extraction, listing the most frequent unigrams and bigrams across all extracted phrases, making prompt-derived meta-vocabulary visible
- [ ] The extraction prompt is revised so that corpus framing (e.g. "UK public dialogue report") is either removed or replaced with neutral wording
- [ ] A curated meta-vocabulary stop-list (e.g. containing "public dialogue", "dialogue participants", "engagement process") is documented and applied or assessed
- [ ] After any prompt revision, the frequency diagnostic is re-run to confirm that prompt-derived terms are no longer over-represented relative to a plausible baseline

## Notes

The appropriate fix for the prompt may not be simply removing the framing — the LLM may need some context to perform well. The CIP should evaluate alternatives (e.g. keeping context but instructing the model explicitly not to use dialogue-process vocabulary). The acceptance criteria for "not over-represented" will need an operationalisation (e.g. no meta-vocabulary term in the top 20 bigrams by frequency).

## References

- **Related Tenets**: (none defined yet for this project)
- **External Links**: See `public_dialogue_analyser_v12b_4.ipynb` — `extract_concerns_from_paragraph` and `extract_benefits_from_paragraph` function prompts; `cluster_labels.json` for evidence of "dialogue" vocabulary in cluster labels

## Progress Updates

### 2026-05-07
Requirement proposed based on Jess's observation about "public dialogue" appearing frequently in concerns and benefits outputs, and on analysis of the extraction prompt structure.
