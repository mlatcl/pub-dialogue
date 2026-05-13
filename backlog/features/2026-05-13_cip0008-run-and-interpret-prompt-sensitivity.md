---
id: "2026-05-13_cip0008-run-and-interpret-prompt-sensitivity"
title: "Run prompt sensitivity analysis on full corpus and interpret results for paper"
status: "Ready"
priority: "High"
created: "2026-05-13"
last_updated: "2026-05-13"
category: "features"
related_cips: ["0008"]
owner: ""
dependencies: []
tags:
- backlog
- cip0008
- prompt-sensitivity
- paper
---

# Task: Run prompt sensitivity analysis on full corpus and interpret results for paper

## Description

`run_prompt_sensitivity` is implemented and the Section 10C cells exist in
`05_robustness.ipynb`. This task covers actually executing the analysis (requires
live OpenAI API access) and interpreting the results to determine whether paper
claims need qualifying.

The function tests 3 prompt variants (A_current, B_paraphrase, C_minimal) for
both concerns and benefits on a stratified sample of 200 chunks. It writes:
- `outputs/prompt_sensitivity_report_concern.csv`
- `outputs/prompt_sensitivity_report_benefit.csv`
- `outputs/prompt_sensitivity_summary_concern.txt`
- `outputs/prompt_sensitivity_summary_benefit.txt`

## Acceptance Criteria

- [ ] Section 10C cells in `05_robustness.ipynb` execute without error
- [ ] `prompt_sensitivity_report_concern.csv` and `_benefit.csv` written to `outputs/`
- [ ] `prompt_sensitivity_summary_concern.txt` and `_benefit.txt` written to `outputs/`
- [ ] yield_agreement ≥ 85% for all variant pairs (or paper claim adjusted)
- [ ] phrase_agreement ≥ 70% for all variant pairs (or paper claim adjusted)
- [ ] One sentence added to paper methods section documenting prompt robustness finding

## Implementation Notes

Run from `05_robustness.ipynb` Section 10C. Requires:
- `OPENAI_API_KEY` set in environment or `.env`
- `paragraph_chunks.csv` present in `outputs/` (produced by `01_processing.ipynb`)
- Approx. 600 LLM calls (200 chunks × 3 variants × 2 kinds); cost ~$0.10–0.20 at gpt-4o-mini

If either metric falls below threshold, add a sentence to the paper noting
that specific findings are robust to prompt variation (or noting where they are not).

## Related

- CIP: 0008

## Progress Updates

### 2026-05-13

Task created. Code implementation complete (CIP-0008 Implemented). Awaiting live run.
