---
id: "0006"
title: "Assessment work is question-agnostic and independently reusable"
status: "Proposed"
priority: "High"
created: "2026-05-12"
last_updated: "2026-05-12"
related_tenets: ["access-assess-address"]
stakeholders: ["Neil Lawrence", "Jess"]
tags: ["pipeline", "assess", "reproducibility", "reusability", "access-assess-address"]
---

# REQ-0006: Assessment work is question-agnostic and independently reusable

## Description

The public dialogue analysis pipeline currently conflates three stages — loading data, characterising data quality, and extracting research-specific findings — into a single notebook execution path. The assessment stage (data quality plots, chunk quality heuristics, corpus statistics) should be separable from the address stage (LLM extraction, embeddings) so that it can be run independently and its outputs reused by any researcher regardless of their specific research question.

The key principle, following the access/assess/address framework (Lawrence, 2021), is that *assess* work is defined as everything that can be done without knowing the research question. If a function or script requires knowledge of what we are looking for (e.g., which technology terms to filter, which LLM prompt to use), it belongs in *address*, not *assess*.

**Why this matters**: Conflating assess and address means that corpus quality diagnostics are only available after incurring LLM API costs. It also prevents the data characterisation work from being reused by other researchers studying the same corpus with different questions, which limits the scientific value of the assessment.

**Who benefits**: Researchers reusing the public dialogue corpus; future analysts working with the same PDFs for different research questions; anyone auditing the quality of the corpus independently of the specific analysis.

## Acceptance Criteria

- [ ] The assess stage (chunk quality flags, corpus statistics, quality plots) can be run to completion without invoking the OpenAI API or any other LLM
- [ ] Assess outputs are written to disk as standalone artefacts (CSV, PNG) that do not require re-running any LLM or embedding calls to regenerate
- [ ] A researcher with a different research question could run only the access and assess stages on the same corpus and obtain useful, unbiased characterisation of the data
- [ ] The boundary between access, assess, and address is reflected in the code structure of the `pub_dialogue` package (e.g., distinct modules) and documented

## Notes

This requirement does not prescribe *how* the separation is achieved (that is the role of CIP-000D). The implementation could use separate Python modules, separate scripts, or separate notebook sections — the requirement is about the outcome (separability and reusability), not the mechanism.

The access/assess/address framework is described in Neil Lawrence's 2021 talk: "Access, Assess and Address: A Pipeline for (Automated?) Data Science", presented at the ECML Workshop on Automating Data Science.

## References

- **Related Tenets**: [access-assess-address](../tenets/pub-dialogue/access-assess-address.md)
- **External Links**: [Lawrence (2021) — Access, Assess, Address](https://inverseprobability.com/talks/notes/access-assess-address-a-pipeline-for-automated-data-science.html)

## Progress Updates

### 2026-05-12
Requirement created alongside the `access-assess-address` project tenet. CIP-000D will describe the implementation approach.
