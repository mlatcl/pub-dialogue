---
id: "2026-05-07_fix-sensitivity-call-sites-and-outputs"
title: "Update sensitivity call sites in notebook and verify output files"
status: "Completed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "bugs"
related_cips: ["0002"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_write-run-sensitivity-function"]
tags:
- backlog
- sensitivity
- bug-fix
- notebook
---

# Task: Update sensitivity call sites in notebook and verify output files

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Once `run_sensitivity` exists in `dialogue_utils.py` (previous task), update the notebook to remove the two duplicate `run_for_k` definitions and replace them with calls to `du.run_sensitivity(...)`. Then run the full sensitivity pass for both tracks and verify that all output files are produced with correct names and content.

Also rename or regenerate the existing `outputs/sensitivity_*` files (which have ambiguous names and may reflect concern or benefit data indiscriminately).

## Acceptance Criteria

- [ ] Part IV.A no longer contains a `def run_for_k` definition; instead calls `du.run_sensitivity(k, "concern", embeddings_normalized, concerns_df, OUTPUT_FOLDER)`
- [ ] Part IV.B no longer contains a `def run_for_k` definition; instead calls `du.run_sensitivity(k, "benefit", benefits_embeddings_normalized, benefits_df, OUTPUT_FOLDER)`
- [ ] After a full sensitivity run, `outputs/` contains all of the following for k ∈ {60, 75, 90}:
  - `concern_sensitivity_stable_core_k{k}.csv`
  - `concern_sensitivity_fingerprint_k{k}.html`
  - `concern_sensitivity_time_metrics_k{k}.csv`
  - `concern_sensitivity_entropy_k{k}.png`
  - `concern_sensitivity_lens_k{k}.csv`
  - `concern_sensitivity_radar_k{k}.html`
  - `benefit_sensitivity_stable_core_k{k}.csv`
  - `benefit_sensitivity_fingerprint_k{k}.html`
  - (and equivalent benefit files for each output type)
- [ ] No file named `sensitivity_*` (without concern/benefit prefix) remains in `outputs/`
- [ ] Opening `concern_sensitivity_fingerprint_k75.html` and `benefit_sensitivity_fingerprint_k75.html` shows labels reading "Concern" and "Benefit" respectively

## Implementation Notes

The old `outputs/sensitivity_*` files can be archived to `outputs/archive/sensitivity_old/` before deletion, in case the previous results need to be referenced. Do not delete them without archiving.

If a full re-run is expensive (API costs), the sensitivity section uses only embeddings and dataframes that are already computed — it does not call the LLM. It can be run from checkpoints without re-running extraction.

## Related

- CIP: 0002
- Documentation: [`cip/cip0002.md`](../../cip/cip0002.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_write-run-sensitivity-function`.

### 2026-05-07 — Completed
Cells 104 and 114 now call run_sensitivity() with kind='concern' and kind='benefit'
respectively. Cell 114 bug fixed (was using concern embeddings for benefit sensitivity).
