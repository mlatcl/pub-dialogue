---
id: "2026-05-14_cip0011-group-d-robustness-cells"
title: "Add stable_core_robustness and lexical_novelty_over_time and restore 05_robustness cells"
status: "Ready"
priority: "High"
created: "2026-05-14"
last_updated: "2026-05-14"
category: "features"
related_cips: ["0011"]
owner: ""
dependencies: []
tags:
- backlog
- address
- robustness
- notebooks
---

# Task: Add stable_core_robustness and lexical_novelty_over_time and restore 05_robustness cells

## Description

`05_robustness.ipynb` has placeholder comment cells for four analyses that are present as
working code in `main-version.ipynb`:

- `main[101]` — "Assess robustness of stable core and AI fingerprint (concerns)"
- `main[111]` — "Assess robustness of stable core and AI fingerprint (benefits)"
- `main[103]` — "Assess lexical novelty in AI concerns over time"
- `main[113]` — "Assess lexical novelty in AI benefits over time"

The stable-core robustness analysis bootstraps document samples and checks whether the
top-20 AI-distinctive concern clusters are stable across samples (Jaccard similarity and
rank correlation). `address.ai_fingerprint_over_crosscut()` already exists; a new wrapper
`address.stable_core_robustness(df, embeddings, kind, n_trials=20)` is needed to package
the bootstrap loop and return a summary DataFrame.

The lexical novelty analysis computes year-on-year Jaccard similarity of the concern/benefit
phrase vocabulary for AI dialogues, and plots the novelty curve over time. A new
`address.lexical_novelty_over_time(df, kind)` function is needed.

## Acceptance Criteria

**Library (`pub_dialogue/address.py`):**
- [ ] `address.stable_core_robustness(df, embeddings, kind, n_trials=20)` implemented
  - Inputs: phrase DataFrame (`concerns_df` or `benefits_df`), embeddings array,
    `kind` (`"concern"` | `"benefit"`), number of bootstrap trials
  - Each trial: sample 80 % of unique documents, recompute AI fingerprint over cross-cutting
    clusters, record top-20 cluster IDs
  - Returns a DataFrame with columns `trial`, `top20_clusters`, `jaccard_vs_full`,
    `rank_corr_vs_full` plus a printed text summary
  - Unit test with small synthetic data (≥ 3 trials)
- [ ] `address.lexical_novelty_over_time(df, kind)` implemented
  - Inputs: phrase DataFrame, `kind`
  - For each consecutive year pair, tokenise phrase text and compute Jaccard similarity
    of token sets
  - Returns a DataFrame with columns `year_from`, `year_to`, `jaccard_similarity`,
    `new_tokens`, `lost_tokens`
  - Unit test with synthetic phrase list spanning 3 years

**Notebook (`05_robustness.ipynb`):**
- [ ] Placeholder comment cells for stable-core robustness (concern + benefit) replaced
      with working cells calling `_address.stable_core_robustness(...)`
- [ ] Placeholder comment cells for lexical novelty (concern + benefit) replaced with
      working cells calling `_address.lexical_novelty_over_time(...)` and plotting the result
- [ ] All four cells are address-phase only (load pre-computed artefacts, no raw data access)

## Implementation Notes

The stable-core bootstrap should use `random.seed` for reproducibility — accept an optional
`seed` parameter defaulting to `42`.

For lexical novelty, the tokeniser from `main-version.ipynb` splits on non-alphanumeric
characters and lowercases; replicate this exactly rather than introducing a new dependency.

The novelty plot uses `matplotlib` (consistent with `main-version.ipynb`) not `plotly`
because it is a simple line chart — keep it simple.

## Related

- CIP: 0011
- Source cells: `main-version.ipynb` cell indices 101, 103, 111, 113
  (code-cell positions 75, 77, 82, 84)
- `notebook_cell_mapping.json` entries: `main_cell_pos: 75, 77, 82, 84`

## Progress Updates

### 2026-05-14
Task created (Proposed → Ready). Two new library functions required; higher complexity than
Groups A–C.
