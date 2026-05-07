---
id: "2026-05-07_write-extraction-yield-diagnostics"
title: "Update extraction loops to collect ExtractionResult and write yield diagnostic files"
status: "Completed"
priority: "High"
created: "2026-05-07"
last_updated: "2026-05-07"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-05-07_add-extraction-result-dataclass"]
tags:
- backlog
- extraction
- diagnostics
- yield
---

# Task: Update extraction loops to collect ExtractionResult and write yield diagnostic files

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Update the extraction loops in the notebook (concerns and benefits) to collect `ExtractionResult` objects rather than bare lists, then compute and write three diagnostic output files that break down the extraction yield into its three root causes.

The three output files:
- `extraction_yield_summary.csv` — counts and percentages for: total chunks, sentinel empties, filter drop chunks, filter drop phrases (total), error chunks, retained phrases
- `tech_filter_drops.csv` — one row per dropped phrase: `chunk_id`, `track` (concern/benefit), `dropped_phrase`, `matching_tech_word`
- `extraction_errors.log` (or `.csv`) — one row per error: `chunk_id`, `track`, `exception_type`, `exception_message`

A summary table is also printed to the notebook cell output at the end of each extraction run.

## Acceptance Criteria

- [ ] The concern extraction loop collects `ExtractionResult` objects and builds `extracted_concerns.csv` from `retained_phrases` (schema unchanged from current)
- [ ] The benefit extraction loop does the same for `extracted_benefits.csv`
- [ ] `outputs/extraction_yield_summary.csv` is written after each full extraction run with columns: `track`, `total_chunks`, `sentinel_empties`, `filter_drop_chunks`, `filter_drop_phrases_total`, `error_chunks`, `retained_phrases`, `pct_retained`
- [ ] `outputs/tech_filter_drops.csv` is written with columns: `chunk_id`, `track`, `dropped_phrase`, `matching_tech_word`
- [ ] `outputs/extraction_errors.log` is written (or `extraction_errors.csv`) with chunk_id and exception details
- [ ] A human-readable summary table is printed to the notebook cell output at extraction completion
- [ ] Running on a 50-chunk sample produces all three files without error
- [ ] The total counts in `extraction_yield_summary.csv` sum correctly: `sentinel_empties + error_chunks + (chunks with ≥1 retained phrase) + (chunks with 0 retained due to filter) = total_chunks`

## Implementation Notes

The `extracted_concerns.csv` and `extracted_benefits.csv` schemas must remain unchanged — they are inputs to the embedding and clustering cells. Only the extraction loop changes; downstream cells are unaffected.

The checkpoint logic (`save_checkpoint` / `load_checkpoint`) should save the list of `ExtractionResult` objects. The checkpoint file name can remain the same; the content changes from `list[list[str]]` to `list[ExtractionResult]`. If a pre-existing checkpoint was saved in the old format, add a migration step that loads the old format and creates minimal `ExtractionResult` objects (with empty `dropped_by_filter` and `error=None`).

## Related

- CIP: 0001
- Documentation: [`cip/cip0001.md`](../../cip/cip0001.md)

## Progress Updates

### 2026-05-07
Task created. Depends on `2026-05-07_add-extraction-result-dataclass`.

### 2026-05-07 — Completed
write_extraction_diagnostics() added to dialogue_utils.py.
Writes: extraction_yield_summary.csv, tech_filter_drops_{kind}.csv, extraction_errors_{kind}.csv.
Notebook cells 14 and 53 updated to collect ExtractionResult lists and call the function.
7 new tests added (85 total, all passing).
